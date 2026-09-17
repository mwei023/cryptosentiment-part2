"""Forward paper-trade journal — the only performance claim that will matter.

E006 dual-arm (price-only vs information-enhanced):
- Each coin-day logs ONE row with BOTH arms side by side from identical
  inputs (same bands, same price, same headlines). The arms differ in
  exactly one place: the info arm applies the pre-registered FinBERT
  majority veto (see papertrade.gate_with_sentiment); the price arm
  never touches news.
- Settlement scores each non-HOLD arm against the next day's close
  (the 1-day horizon the system claims), with identical costs
  (0.3% round-trip). A vetoed HOLD settles nothing — the veto's value
  is measured by the price arm's outcome on veto days (counterfactual
  ledger in E006), not by inventing fills.
- Migration: V1 files (signal/confidence/net_pct/win columns) are
  upgraded in place on first write — old rows were all unsettled
  HOLDs, so signal_price = signal_info = old signal and
  conf_info = old confidence. No history is rewritten.

Usage: run ``log_today('bitcoin')`` once per day (cron/Celery beat at
00:05 UTC, or manually). After 30+ settled signals PER ARM,
``summary()`` and ``research/e006_price_vs_info.py`` report the
head-to-head — that table, not any backtest, decides whether news
ever touches real capital.
"""

import csv
import os

JOURNAL = os.path.join(os.path.dirname(__file__), "../paper_journal.csv")

# V2 dual-arm columns (E006). settle_price is shared (same next close);
# each arm has its own net/win so HOLD-veto days score only the arm
# that actually traded.
COLUMNS = ["date", "coin_id", "price", "band_lower", "band_upper",
           "band_position", "n_news", "n_pos", "n_neg", "n_neu", "vol",
           "conf_price", "conf_info",
           "signal_price", "signal_info",
           "settle_price", "net_price", "net_info",
           "win_price", "win_info"]

# V1 columns (pre-E006) — recognized for migration only.
_V1_COLUMNS = ["date", "coin_id", "signal", "price", "band_lower",
               "band_upper", "band_position", "n_news", "n_pos",
               "n_neg", "n_neu", "confidence", "settle_price",
               "net_pct", "win"]


def _ensure():
    if not os.path.exists(JOURNAL):
        with open(JOURNAL, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()
        return
    with open(JOURNAL, newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
    if header == COLUMNS:
        return
    if header == _V1_COLUMNS:
        _migrate_v1()
        return
    raise RuntimeError(f"Unknown journal schema: {header}")


def _migrate_v1():
    """Upgrade a V1 journal to V2. Old rows were unsettled HOLDs:
    both arms inherit the old signal; conf_info inherits the old
    confidence; price-arm settlement columns start empty."""
    with open(JOURNAL, newline="") as f:
        old = list(csv.DictReader(f))
    new_rows = []
    for r in old:
        new_rows.append({
            "date": r["date"], "coin_id": r["coin_id"],
            "price": r["price"], "band_lower": r["band_lower"],
            "band_upper": r["band_upper"],
            "band_position": r["band_position"],
            "n_news": r["n_news"], "n_pos": r["n_pos"],
            "n_neg": r["n_neg"], "n_neu": r["n_neu"], "vol": "",
            "conf_price": "", "conf_info": r["confidence"],
            "signal_price": r["signal"], "signal_info": r["signal"],
            "settle_price": r["settle_price"], "net_price": "",
            "net_info": "",
            "win_price": "", "win_info": "",
        })
    with open(JOURNAL, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(new_rows)


def _today():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _settle_row(r, settle_px):
    """Score both arms against the same settlement price. Returns
    True if either arm settled."""
    entry = float(r["price"])
    changed = False
    for arm, sig_key, net_key, win_key in (
        ("price", "signal_price", "net_price", "win_price"),
        ("info", "signal_info", "net_info", "win_info"),
    ):
        if r[net_key] or r[sig_key] == "HOLD":
            continue
        gross = (settle_px - entry) / entry
        if r[sig_key] == "SELL":
            gross = -gross  # paper short of our own band call; flat bookkeeping
        net = gross - 0.003  # round-trip costs, same as backtest
        r[net_key] = f"{net * 100:.3f}"
        r[win_key] = "1" if net > 0 else "0"
        changed = True
    if changed:
        r["settle_price"] = str(settle_px)
    return changed


def settle_pending():
    """Score any rows with an unsettled trading arm against today's
    closes. Returns the count of rows with at least one settled arm."""
    from utils.market_data import get_latest_price
    _ensure()
    with open(JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))
    changed = False
    for r in rows:
        needs = ((r["signal_price"] != "HOLD" and not r["net_price"])
                 or (r["signal_info"] != "HOLD" and not r["net_info"]))
        if not needs:
            continue
        px = get_latest_price(r["coin_id"])
        if px is None:
            continue
        if _settle_row(r, px):
            changed = True
    if changed:
        with open(JOURNAL, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
    return sum(1 for r in rows if r["net_price"] or r["net_info"])


def log_today(coin_id):
    """Settle old rows, then append today's dual-arm signal. Returns
    the row."""
    from utils.papertrade import daily_signal_dual
    settled = settle_pending()
    sig = daily_signal_dual(coin_id)
    if "error" in sig:
        return {"coin_id": coin_id, "error": sig["error"], "settled": settled}
    _ensure()
    with open(JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))
    if any(r["date"] == _today() and r["coin_id"] == coin_id for r in rows):
        return {"coin_id": coin_id, "skipped": "already logged today", "settled": settled}
    row = {
        "date": _today(), "coin_id": coin_id,
        "price": sig["price"], "band_lower": sig["band"]["lower"],
        "band_upper": sig["band"]["upper"], "band_position": sig["band_position"],
        "n_news": sig["sentiment"]["n"], "n_pos": sig["sentiment"]["pos"],
        "n_neg": sig["sentiment"]["neg"], "n_neu": sig["sentiment"]["neu"],
        "vol": sig.get("vol", ""),
        "conf_price": sig["conf_price"], "conf_info": sig["conf_info"],
        "signal_price": sig["signal_price"], "signal_info": sig["signal_info"],
        "settle_price": "", "net_price": "", "net_info": "",
        "win_price": "", "win_info": "",
    }
    with open(JOURNAL, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=COLUMNS).writerow(row)
    row["settled"] = settled
    return row


def read_rows():
    """Return all journal rows as dicts (typed by _ensure / migration).

    Read-only view for the API layer: /research/journal serializes this
    for the frontend P&L chart. No settling happens here — settlement
    is a write-path concern (settle_pending / log_today).
    """
    _ensure()
    with open(JOURNAL, newline="") as f:
        return list(csv.DictReader(f))


def _arm_stats(rows, net_key, win_key):
    nets = [float(r[net_key]) for r in rows if r[net_key]]
    if not nets:
        return {"settled": 0}
    wins = [n for n in nets if n > 0]
    gp, gl = sum(wins), abs(sum(n for n in nets if n <= 0))
    return {
        "settled": len(nets),
        "wins": len(wins),
        "losses": len(nets) - len(wins),
        "win_rate_pct": round(len(wins) / len(nets) * 100, 1),
        "expectancy_pct": round(sum(nets) / len(nets), 3),
        "total_net_pct": round(sum(nets), 2),
        "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
    }


def summary():
    """Head-to-head table over settled (forward-tested) arms only.
    Legacy callers get the info arm under the old keys."""
    _ensure()
    with open(JOURNAL, newline="") as f:
        rows = list(csv.DictReader(f))
    settled = [r for r in rows if r["net_price"] or r["net_info"]]
    if not settled:
        return {"settled": 0, "note": "no settled signals yet — journal just started"}
    price = _arm_stats(settled, "net_price", "win_price")
    info = _arm_stats(settled, "net_info", "win_info")
    vetoes = sum(1 for r in settled
                 if r["signal_price"] != "HOLD"
                 and r["signal_info"] == "HOLD")
    return {
        "settled_rows": len(settled),
        "vetoes": vetoes,
        "price": price,
        "info": info,
        # backward compat: old keys mirror the info arm
        "settled": info.get("settled", 0),
        "wins": info.get("wins", 0),
        "losses": info.get("losses", 0),
        "win_rate_pct": info.get("win_rate_pct", 0.0),
        "expectancy_pct": info.get("expectancy_pct", 0.0),
        "total_net_pct": info.get("total_net_pct", 0.0),
    }
