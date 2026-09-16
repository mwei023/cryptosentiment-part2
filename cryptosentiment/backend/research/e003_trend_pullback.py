"""E003 — Trend Pullback Entry (H002).

Head-to-head under identical data, costs, and foundation:
  S001 (V1 control): close < lower band -> enter (standing control)
  S003 (H002):       SMA20 > SMA50 yesterday -> yesterday pulled back
                     below SMA20 -> today reclaims SMA20 -> today breaks
                     yesterday's high -> enter (trend-aligned entry)

Everything except the entry trigger is frozen F001 (D002). Pre-registered
verdict rules (before any run): pooled trades < 10 -> INCONCLUSIVE
(no verdict from a sample that small); ADVANCED requires positive pooled
expectancy AND beating the control; otherwise REJECTED.

Also reports trigger/gate compatibility (E002's lesson): a treatment
that fires only while the gate is closed is structurally dead regardless
of its numbers.

Run from backend/:  ./cryptoenv/bin/python -m research.e003_trend_pullback
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import foundation  # noqa: E402
from research import strategies  # noqa: E402

EXPERIMENT_ID = "E003"
HYPOTHESIS_ID = "H002"
FOUNDATION_ID = "F001"
COINS = ("bitcoin", "ethereum", "solana")
CAPITAL = 10_000.0
MIN_POOLED_TRADES = 10  # pre-registered

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)


def print_row(name, d):
    pf = d.get("profit_factor", 0)
    pf = "    --" if pf is None else ("inf" if pf == float("inf") else f"{pf:.2f}")

    def _f(v, spec):
        return "      --" if v is None else format(v, spec)

    wr = d.get("win_rate")
    wr = "   --" if wr is None else f"{wr * 100:>6.1f}%"
    print(f"{name:<26} {d.get('n_trades', d.get('trades', 0)):>7}  "
          f"{pf:>7}  {_f(d.get('expectancy_pct'), '+9.2f')}%  "
          f"{wr:>6}  {_f(d.get('total_return_pct'), '+9.2f')}%  "
          f"{_f(d.get('max_drawdown_pct'), '7.2f')}%")


def main():
    started = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"E003 — TREND PULLBACK ENTRY (H002)  |  foundation {FOUNDATION_ID} frozen")
    print("=" * 70)
    print(f"Started: {started.isoformat()}")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    print(f"Git: {commit}   Python: {platform.python_version()}   Capital: ${CAPITAL:,.0f}")
    print("Control:   S001 V1  = close below lower band -> BUY (standing control)")
    print("Treatment: S003 H002 = SMA20>SMA50 -> pullback below SMA20 -> reclaim")
    print("                      SMA20 -> break yesterday's high -> BUY")
    print("Everything else identical (gates/sizing/stops/targets/trail/kill/costs).")
    print(f"Pre-registered: pooled trades < {MIN_POOLED_TRADES} -> INCONCLUSIVE.\n")

    results = {}
    header = (f"{'strategy':<26} {'trades':>7}  {'PF':>7}  {'exp/trade':>10}  "
              f"{'win%':>6}  {'return':>10}  {'maxDD':>8}")
    for coin in COINS:
        print(f"--- {coin.upper()} (identical Binance daily tape, ~2.7y) ---")
        print(header)
        v1 = foundation.run(coin, capital=CAPITAL, source="binance")
        v1.pop("trades", None)
        s3 = strategies.run_pullback(coin, capital=CAPITAL, source="binance")
        s3_trades = s3.pop("trades")
        diag = s3.pop("trigger_diag")
        rejections = s3.pop("rejections")

        daily, _, _ = foundation.load_data(coin, 365, "binance")
        closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
        bh = round((closes[-1] / closes[foundation.SMA_LONG] - 1) * 100, 2)
        bh_row = {"n_trades": 1, "profit_factor": None,
                  "expectancy_pct": bh, "win_rate": None,
                  "total_return_pct": bh, "max_drawdown_pct": None}

        print_row("buy_hold (same window)", bh_row)
        print_row("S001 V1 band_revert (control)", v1)
        print_row("S003 trend_pullback (H002)", s3)
        print(f"    triggers: fired {diag['fired']} (gate open {diag['fired_gate_open']} / "
              f"closed {diag['fired_gate_closed']}) | blocked: in-pos {diag['already_in']}, "
              f"standdown {diag['standdown']}, no-atr {diag['no_atr']}")
        if s3_trades:
            for t in s3_trades:
                print(f"      trade: bar {t['entry_i']}->{t['exit_i']} {t['reason']:7s} "
                      f"entry {t['entry']:.0f} exit {t['exit']:.0f} net {t['net_pct']:+.2f}%")
        print()

        results[coin] = {"v1": v1, "s003": s3, "buy_hold_pct": bh,
                         "trigger_diag": diag, "s003_trades": s3_trades,
                         "s003_rejections": rejections}

    # ---- pooled verdict (explicit pooling over stored per-coin ledgers) ----
    def pool_v1():
        trades, wins, nets = 0, 0, []
        for c in COINS:
            r = foundation.run(c, capital=CAPITAL, source="binance")
            trades += r["n_trades"]
            wins += r["wins"]
            nets += [t["net_pct"] for t in r["trades"]]
        gp = sum(x for x in nets if x > 0)
        gl = abs(sum(x for x in nets if x <= 0))
        return {"trades": trades, "wins": wins,
                "win_rate": round(wins / trades, 3) if trades else 0.0,
                "expectancy_pct": round(sum(nets) / len(nets), 3) if nets else 0.0,
                "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
                "total_net_pct": round(sum(nets), 2)}

    def pool_s3():
        trades, wins, nets = 0, 0, []
        for c in COINS:
            for t in results[c]["s003_trades"]:
                trades += 1
                nets.append(t["net_pct"])
                wins += 1 if t["net_pct"] > 0 else 0
        gp = sum(x for x in nets if x > 0)
        gl = abs(sum(x for x in nets if x <= 0))
        return {"trades": trades, "wins": wins,
                "win_rate": round(wins / trades, 3) if trades else 0.0,
                "expectancy_pct": round(sum(nets) / len(nets), 3) if nets else 0.0,
                "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
                "total_net_pct": round(sum(nets), 2)}

    print("--- POOLED (3 coins) ---")
    print(header)
    pv1 = pool_v1()
    ps3 = pool_s3()
    pv1_row = dict(pv1, total_return_pct=None, max_drawdown_pct=None)
    ps3_row = dict(ps3, total_return_pct=None, max_drawdown_pct=None)
    print_row("S001 V1 (control)", pv1_row)
    print_row("S003 H002", ps3_row)

    # ---- counterfactual: blocked candidates ----
    blocked = [(c, rj["fwd10"]) for c in COINS
               for rj in results[c]["s003_rejections"] if rj.get("fwd10") is not None]
    if blocked:
        fw = [f for _, f in blocked]
        up = sum(1 for f in fw if f > 0)
        print(f"\n--- COUNTERFACTUAL: blocked candidates ({len(blocked)}) ---")
        print(f"fwd10 mean {sum(fw)/len(fw):+.2f}%  median {sorted(fw)[len(fw)//2]:+.2f}%  up {up}/{len(fw)}")
    else:
        print("\n--- COUNTERFACTUAL: no blocked candidates with fwd data ---")

    # ---- verdict (pre-registered rules) ----
    beat = (ps3["trades"] >= MIN_POOLED_TRADES
            and ps3["expectancy_pct"] > pv1["expectancy_pct"]
            and ps3["profit_factor"] > pv1["profit_factor"])
    positive = ps3["expectancy_pct"] > 0
    if ps3["trades"] < MIN_POOLED_TRADES:
        status = "INCONCLUSIVE"
        why = (f"only {ps3['trades']} pooled trades (< {MIN_POOLED_TRADES} pre-registered "
               f"minimum); no verdict from this sample")
    elif beat and positive:
        status = "ADVANCED"
        why = "positive expectancy and beats control"
    elif not positive:
        status = "REJECTED"
        why = "pooled expectancy not positive after costs"
    else:
        status = "INCONCLUSIVE"
        why = "positive expectancy but did not beat control on both metrics"

    print(f"\nVERDICT: {status} — {why}")
    print(f"  S003: {ps3['trades']} trades, exp {ps3['expectancy_pct']:+.2f}%, "
          f"PF {ps3['profit_factor']} | V1: {pv1['trades']} trades, "
          f"exp {pv1['expectancy_pct']:+.2f}%, PF {pv1['profit_factor']}")

    finished = datetime.now(timezone.utc)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "foundation_id": FOUNDATION_ID,
        "control": "S001 band_revert (foundation.run)",
        "treatment": "S003 trend_pullback (research.strategies.run_pullback)",
        "started": started.isoformat(), "finished": finished.isoformat(),
        "git_commit": commit, "python": platform.python_version(),
        "capital": CAPITAL,
        "costs": "0.1% fee + 0.05% slippage per side",
        "data": "Binance daily OHLC, 1000 bars/coin (~2.7y)",
        "pre_registered_rules": {
            "min_pooled_trades_for_verdict": MIN_POOLED_TRADES,
            "advanced_requires": "positive pooled expectancy AND beats control",
        },
        "results": results,
        "pooled_v1": pv1,
        "pooled_s003": ps3,
        "verdict": {"status": status, "reason": why},
    }
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")


if __name__ == "__main__":
    main()
