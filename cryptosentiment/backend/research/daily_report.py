"""Daily automation: log, settle, compare, look ahead. Printable.

One command runs the whole loop for all coins::

    ./cryptoenv/bin/python -m research.daily_report        # log + print
    ./cryptoenv/bin/python -m research.daily_report --print-only   # no logging

What it does:
  1. LOG — journal.log_today() per coin (settles yesterday's open arms
     against today's closes, then appends today's dual-arm row).
  2. COMPARE — head-to-head price-vs-info from journal.summary(),
     diffed against the previous saved report (settled/vetoes/
     expectancy deltas) so each day shows movement, not just levels.
  3. NOW vs OTHER — per coin: price arm vs info arm (signals, conf
     spread, veto flag with pos/neg cause).
  4. NEXT — settlement watch (which arms logged today will settle
     tomorrow), band distances (% move that flips each arm), and the
     E006 maturity countdown (settled/arm vs 30 required).

Receipts: research/results/E006/daily_reports/YYYY-MM-DD.json — the
previous file is the baseline for tomorrow's diff. Cron fallback
(no Redis)::

    5 0 * * * cd /path/to/backend && ./cryptoenv/bin/python -m research.daily_report >> paper_reports.log 2>&1

(Celery beat runs the same entry point via tasks.run_daily_journal.)
"""

import argparse
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COINS = ("bitcoin", "ethereum", "solana")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "results",
                           "E006", "daily_reports")
MIN_SETTLED = 30


def _today():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def run_daily():
    """Settle + log every coin. Returns {coin: row}."""
    from utils import journal
    out = {}
    for coin in COINS:
        try:
            out[coin] = journal.log_today(coin)
        except Exception as e:  # one coin's failure never blocks the others
            out[coin] = {"coin_id": coin, "error": str(e)}
    return out


def _load_reports():
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "*.json")))
    return files


def _fmt_pct(x):
    return f"{x:+.2f}%" if isinstance(x, (int, float)) else "--"


def _band_watch(row):
    """% moves from today's price that flip each arm tomorrow.

    Bands move daily, so these are first-order guides (frozen-band
    approximation), not promises. Returns human-readable watch line.
    """
    try:
        px = float(row["price"])
        lo = float(row["band_lower"])
        hi = float(row["band_upper"])
    except (KeyError, TypeError, ValueError):
        return "band data unavailable"
    pos = row.get("band_position", "?")
    to_buy = (px - lo) / px * 100   # down-move needed to reach lower band
    to_sell = (hi - px) / px * 100  # up-move needed to reach upper band
    if row.get("signal_price") == "BUY":
        return (f"price-BUY open: a hold above {lo:,.2f} "
                f"(+{abs(px - lo) / px * 100:.1f}% cushion) keeps it; "
                f"info arm: {row.get('signal_info')}")
    if row.get("signal_price") == "SELL":
        return (f"price-SELL open: a hold below {hi:,.2f} keeps it; "
                f"info arm: {row.get('signal_info')}")
    return (f"inside: -{to_buy:.1f}% day reaches BUY zone "
            f"({lo:,.2f}), +{to_sell:.1f}% day reaches SELL zone "
            f"({hi:,.2f}) [{pos}]")


def build_report(logged):
    """Combine today's rows + journal head-to-head + previous receipt."""
    from utils import journal
    summ = journal.summary()
    today = _today()

    prev, prev_data = None, {}
    files = [f for f in _load_reports() if not f.endswith(f"{today}.json")]
    if files:
        prev = files[-1]
        try:
            with open(prev) as f:
                prev_data = json.load(f)
        except (OSError, ValueError):
            prev_data = {}

    per_coin = {}
    for coin in COINS:
        r = logged.get(coin, {})
        if "error" in r and "price" not in r:
            per_coin[coin] = {"error": r.get("error", "unknown")}
            continue
        per_coin[coin] = {
            "signal_price": r.get("signal_price"),
            "signal_info": r.get("signal_info"),
            "vetoed": r.get("signal_price") != "HOLD"
            and r.get("signal_info") == "HOLD",
            "conf_price": r.get("conf_price"),
            "conf_info": r.get("conf_info"),
            "band_position": r.get("band_position"),
            "sentiment": {"n": r.get("n_news"), "pos": r.get("n_pos"),
                          "neg": r.get("n_neg"), "neu": r.get("n_neu")},
            "watch": _band_watch(r) if "price" in r else "already logged today",
            "skipped": r.get("skipped", ""),
        }

    def _delta(cur, old):
        if isinstance(cur, (int, float)) and isinstance(old, (int, float)):
            d = cur - old
            return f"{d:+.2f}" if isinstance(cur, float) else f"{d:+d}"
        return "--"

    prev_summ = prev_data.get("summary", {}) if prev_data else {}
    deltas = {}
    for arm in ("price", "info"):
        cur, old = summ.get(arm, {}), prev_summ.get(arm, {})
        deltas[arm] = {
            "settled": _delta(cur.get("settled"), old.get("settled")),
            "expectancy": _delta(cur.get("expectancy_pct"),
                                 old.get("expectancy_pct")),
        }
    deltas["vetoes"] = _delta(summ.get("vetoes"), prev_summ.get("vetoes"))

    # Maturity countdown: the binding constraint is the slower arm.
    arms_settled = [summ.get(a, {}).get("settled", 0) for a in ("price", "info")]
    slowest = min(arms_settled) if arms_settled else 0
    to_go = max(0, MIN_SETTLED - slowest)

    # Settlement watch: today's non-HOLD arms settle on tomorrow's run.
    settling = {c: {a: per_coin[c].get(f"signal_{a}")
                    for a in ("price", "info")}
                for c in COINS if "error" not in per_coin.get(c, {})}

    return {
        "date": today,
        "summary": summ,
        "deltas_vs": os.path.basename(prev) if prev else None,
        "deltas": deltas,
        "per_coin": per_coin,
        "settling_tomorrow": settling,
        "maturity": {"settled_slowest_arm": slowest,
                     "required_per_arm": MIN_SETTLED,
                     "to_go": to_go},
    }


def format_report(rep):
    """Printable text: compare, now-vs-other, next."""
    L = [f"E006 DAILY — {rep['date']}"]
    s = rep["summary"]
    if s.get("settled_rows", 0) == 0 and s.get("settled", 0) == 0:
        L.append("Journal: no settled arms yet — arms log daily, "
                 "verdict needs 30/arm.")
    else:
        base = (f"vs {rep['deltas_vs']}" if rep["deltas_vs"]
                else "vs nothing (first report)")
        for arm in ("price", "info"):
            a = s.get(arm, {})
            d = rep["deltas"][arm]
            L.append(
                f"{arm:>5}: settled {a.get('settled')} ({d['settled']}), "
                f"exp {_fmt_pct(a.get('expectancy_pct'))} ({d['expectancy']}), "
                f"PF {a.get('profit_factor')}, "
                f"win {a.get('win_rate_pct')}% [{base}]")
        L.append(f"vetoes so far: {s.get('vetoes')} ({rep['deltas']['vetoes']})")

    L.append("--- NOW: price arm vs info arm ---")
    for coin in COINS:
        c = rep["per_coin"].get(coin, {})
        if "error" in c:
            L.append(f"{coin}: ERROR {c['error']}")
            continue
        veto = " VETOED" if c.get("vetoed") else ""
        sn = c.get("sentiment", {})
        L.append(
            f"{coin}: price {c.get('signal_price')} / info "
            f"{c.get('signal_info')}{veto} | conf "
            f"{c.get('conf_price')} vs {c.get('conf_info')} | "
            f"news n={sn.get('n')} pos={sn.get('pos')} "
            f"neg={sn.get('neg')} {c.get('skipped', '')}".rstrip())
    L.append("--- NEXT ---")
    for coin in COINS:
        c = rep["per_coin"].get(coin, {})
        if "error" in c:
            continue
        L.append(f"{coin}: {c.get('watch')}")
    m = rep["maturity"]
    L.append(f"E006 maturity: {m['settled_slowest_arm']}/"
             f"{m['required_per_arm']} per arm, ~{m['to_go']} trading "
             f"days to verdict at current pace.")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="E006 daily automation")
    ap.add_argument("--print-only", action="store_true",
                    help="settle + report without logging new rows")
    args = ap.parse_args(argv)

    logged = {}
    if args.print_only:
        from utils import journal
        journal.settle_pending()
        for coin in COINS:  # show current state; nothing appended
            logged[coin] = {"coin_id": coin, "skipped": "(print-only)"}
        # refresh with real latest rows for the watch section
        with open(journal.JOURNAL, newline="") as f:
            rows = list(csv.DictReader(f))
        for coin in COINS:
            coin_rows = [r for r in rows if r["coin_id"] == coin]
            if coin_rows:
                r = coin_rows[-1]
                logged[coin] = {
                    "coin_id": coin, "signal_price": r["signal_price"],
                    "signal_info": r["signal_info"],
                    "conf_price": r["conf_price"],
                    "conf_info": r["conf_info"],
                    "band_position": r["band_position"],
                    "price": r["price"], "band_lower": r["band_lower"],
                    "band_upper": r["band_upper"], "n_news": r["n_news"],
                    "n_pos": r["n_pos"], "n_neg": r["n_neg"],
                    "n_neu": r["n_neu"],
                    "skipped": "(print-only, latest logged row)",
                }
    else:
        logged = run_daily()

    rep = build_report(logged)
    if not args.print_only:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(os.path.join(REPORTS_DIR, f"{rep['date']}.json"), "w") as f:
            json.dump(rep, f, indent=2, default=str)
    text = format_report(rep)
    print(text)
    return rep


if __name__ == "__main__":
    main()
