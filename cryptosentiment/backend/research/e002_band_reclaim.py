"""E002 — Band Reclaim Entry (H001).

Head-to-head under identical data, costs, and foundation:
  S001 (V1 control): close < lower band -> enter (knife catch)
  S002 (H001):       yesterday below band -> today reclaims it -> breaks
                     yesterday's high -> enter (evidence of reversal)

Everything except the entry trigger is frozen F001 (D002): same gates,
sizing, stops, targets, trail, kill switch, costs. Same candles, same
window, same forced liquidation. The ONLY thing being tested is whether
requiring reversal evidence improves expectancy.

Bonus evidence: the rejection ledger. Every S002 candidate blocked by a
gate is recorded with forward returns (fwd5/fwd10), so we can ask:
"did the trades we blocked go on to lose?"

Run from backend/:  ./cryptoenv/bin/python -m research.e002_band_reclaim
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import foundation  # noqa: E402  (V1-control entries + benchmarks)
from research import strategies  # noqa: E402  (S002)

EXPERIMENT_ID = "E002"
HYPOTHESIS_ID = "H001"
FOUNDATION_ID = "F001"
COINS = ("bitcoin", "ethereum", "solana")
CAPITAL = 10_000.0

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)


def pct(x):
    return f"{x:+.2f}%"


def one(coin, cap=CAPITAL):
    """Run control + treatment on the same coin/window. Returns dict."""
    v1 = foundation.run(coin, capital=cap, source="binance")
    s2 = strategies.run(coin, capital=cap, source="binance")

    # Same-window buy_hold from the SAME binance tape (pure closes path).
    daily, candles, _ = foundation.load_data(coin, 365, "binance")
    closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
    n = len(closes)
    start = min(
        (t["entry_i"] for t in v1["trades"]),
        default=foundation.SMA_LONG,
    )
    # buy_hold over the identical foundation evaluation window
    bh_start = foundation.SMA_LONG
    bh = (closes[n - 1] / closes[bh_start] - 1) * 100 if n > bh_start else 0.0

    # V1's entries that S002 skipped: counterfactual quality of the filter
    v1_entry_idx = {t["entry_i"] for t in v1["trades"]}
    s2_entry_idx = {t["entry_i"] for t in s2["trades"]}
    skipped = sorted(v1_entry_idx - s2_entry_idx)
    skipped_detail = []
    for i in skipped:
        j = min(i + 10, n - 1)
        skipped_detail.append({
            "i": i,
            "v1_net_pct": next((t["net_pct"] for t in v1["trades"] if t["entry_i"] == i), None),
            "fwd10_pct": round((closes[j] / closes[i] - 1) * 100, 2),
        })

    return {"coin_id": coin, "v1": v1, "s002": s2,
            "buy_hold_pct": round(bh, 2),
            "v1_skipped_by_s002": skipped_detail}


def print_row(name, d, keys=("n_trades", "profit_factor", "expectancy_pct",
                             "win_rate", "total_return_pct", "max_drawdown_pct")):
    pf = d.get("profit_factor", 0)
    pf = "    --" if pf is None else ("inf" if pf == float("inf") else f"{pf:.2f}")
    def _f(v, spec):
        return "      --" if v is None else format(v, spec)
    wr = d.get("win_rate")
    wr = "   --" if wr is None else f"{wr * 100:>6.1f}%"
    exp = d.get("expectancy_pct")
    ret = d.get("total_return_pct")
    dd = d.get("max_drawdown_pct")
    print(f"{name:<26} {d.get('n_trades', d.get('trades', 0)):>7}  "
          f"{pf:>7}  {_f(exp, '+9.2f')}%  "
          f"{wr:>6}  "
          f"{_f(ret, '+9.2f')}%  "
          f"{_f(dd, '7.2f')}%")


def main():
    started = datetime.now(timezone.utc)
    print("=" * 70)
    print(f"E002 — BAND RECLAIM ENTRY (H001)  |  foundation {FOUNDATION_ID} frozen")
    print("=" * 70)
    print(f"Started: {started.isoformat()}")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    print(f"Git: {commit}   Python: {platform.python_version()}   Capital: ${CAPITAL:,.0f}")
    print("Control:    S001 V1  = close below lower band -> BUY (knife catch)")
    print("Treatment:  S002 H001 = yesterday below band -> reclaim -> break prev high -> BUY")
    print("Everything else identical (gates/sizing/stops/targets/trail/kill/costs).\n")

    results = {}
    header = (f"{'strategy':<26} {'trades':>7}  {'PF':>7}  {'exp/trade':>10}  "
              f"{'win%':>6}  {'return':>10}  {'maxDD':>8}")
    for coin in COINS:
        print(f"--- {coin.upper()} (identical Binance daily tape) ---")
        print(header)
        r = one(coin)
        results[coin] = r
        bh = {"n_trades": 1, "profit_factor": None,
              "expectancy_pct": r["buy_hold_pct"], "win_rate": None,
              "total_return_pct": r["buy_hold_pct"],
              "max_drawdown_pct": None}
        print_row("buy_hold (same window)", bh)
        print_row("S001 V1 band_revert (control)", r["v1"])
        print_row("S002 band_reclaim (H001)", r["s002"])
        print()

    # ---- pooled verdict ----
    def pool(rs, key):
        trades, wins, nets = 0, 0, []
        for r in rs:
            d = r[key]
            trades += d["n_trades"]
            wins += d["wins"]
            nets += [t["net_pct"] for t in d["trades"]]
        gp = sum(x for x in nets if x > 0)
        gl = abs(sum(x for x in nets if x <= 0))
        return {
            "trades": trades,
            "wins": wins,
            "win_rate": round(wins / trades, 3) if trades else 0.0,
            "expectancy_pct": round(sum(nets) / len(nets), 3) if nets else 0.0,
            "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else 0.0),
            "total_net_pct": round(sum(nets), 2),
        }

    pooled_v1 = pool([results[c] for c in COINS], "v1")
    pooled_s2 = pool([results[c] for c in COINS], "s002")

    # ---- counterfactual analysis of blocked candidates ----
    print("--- COUNTERFACTUAL: S002 candidates blocked by gates ---")
    blocked_all = []
    for coin in COINS:
        for rj in results[coin]["s002"]["rejections"]:
            if rj["trigger"]:
                fwd = rj.get("fwd10")
                if fwd is not None:
                    blocked_all.append((coin, fwd))
    if blocked_all:
        fwds = [f for _, f in blocked_all]
        wins_b = sum(1 for f in fwds if f > 0)
        print(f"blocked candidates with fwd10 data: {len(blocked_all)}")
        print(f"  fwd10 mean {sum(fwds) / len(fwds):+.2f}%  median {sorted(fwds)[len(fwds)//2]:+.2f}%  "
              f"up {wins_b}/{len(fwds)} ({wins_b/len(fwds)*100:.0f}%)")
        print("  (positive mean = the gates blocked MISSED opportunities;")
        print("   negative mean = the gates blocked LOSERS = the filter is earning its keep)")
    else:
        print("no blocked candidates had trigger=True — all candidates passed the gates")

    print("\n--- COUNTERFACTUAL: V1 entries S002 skipped ---")
    for coin in COINS:
        det = results[coin]["v1_skipped_by_s002"]
        if det:
            nets = [d["v1_net_pct"] for d in det if d["v1_net_pct"] is not None]
            fw = [d["fwd10_pct"] for d in det]
            print(f"{coin}: skipped {len(det)} V1 entries | "
                  f"V1-trade net {sum(nets)/len(nets):+.2f}%/trade | "
                  f"blind fwd10 {sum(fw)/len(fw):+.2f}%")
        else:
            print(f"{coin}: skipped 0 V1 entries")

    print("\n--- POOLED (3 coins) ---")
    print_row("S001 V1 (control)", pooled_v1)
    print_row("S002 H001", pooled_s2)

    beat = (pooled_s2["expectancy_pct"] > pooled_v1["expectancy_pct"]
            and pooled_s2["profit_factor"] > pooled_v1["profit_factor"])
    print(f"\nVERDICT: S002 {'BEATS' if beat else 'does NOT beat'} control "
          f"(exp {pct(pooled_s2['expectancy_pct'])} vs {pct(pooled_v1['expectancy_pct'])}; "
          f"PF {pooled_s2['profit_factor']} vs {pooled_v1['profit_factor']})")
    if pooled_s2["expectancy_pct"] <= 0:
        print("STATUS: REJECTED — treatment expectancy still not positive after costs")
    elif beat:
        print("STATUS: ADVANCED — proceed to out-of-sample window (untouched period)")
    else:
        print("STATUS: INCONCLUSIVE — mixed vs control")

    finished = datetime.now(timezone.utc)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "foundation_id": FOUNDATION_ID,
        "control": "S001 band_revert (foundation.run)",
        "treatment": "S002 band_reclaim (research.strategies.run)",
        "started": started.isoformat(), "finished": finished.isoformat(),
        "git_commit": commit, "python": platform.python_version(),
        "capital": CAPITAL,
        "costs": "0.1% fee + 0.05% slippage per side",
        "data": "Binance daily OHLC, 1000 bars/coin",
        "results": results,
        "pooled_v1": pooled_v1,
        "pooled_s002": pooled_s2,
        "verdict": {
            "s002_beats_control": bool(beat),
            "pooled_s002_expectancy_positive": pooled_s2["expectancy_pct"] > 0,
            "status": ("ADVANCED" if beat and pooled_s2["expectancy_pct"] > 0
                       else "REJECTED" if pooled_s2["expectancy_pct"] <= 0
                       else "INCONCLUSIVE"),
        },
    }
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")


if __name__ == "__main__":
    main()
