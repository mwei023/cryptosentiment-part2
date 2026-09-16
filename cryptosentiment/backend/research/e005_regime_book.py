"""E005 — Regime-Conditional Book (H004), dev vs out-of-sample.

The book (authorized by D006, composition of already-tested cells):
  BULL_RANGE -> V1 band-revert trigger
  BULL_TREND -> S003 trend-pullback trigger
  everything else -> flat
Coin-agnostic (same cells for BTC/ETH/SOL — no per-coin selection).

SPLIT (pre-registered before any E005 number existed):
  bars 200-760  : DEVELOPMENT (in-sample)
  bars 760-1000 : OUT-OF-SAMPLE — untouched by any prior experiment's
                  verdict logic except E004's full-window attribution,
                  which is disclosed as a leak and handled by reporting
                  the dev-window attribution as a consistency check
                  WITHOUT re-selecting cells (D006 named the cells; they
                  stay regardless of what dev says).

VERDICT RULES (pre-registered):
  pooled OOS trades < 5        -> INCONCLUSIVE
  pooled OOS expectancy > 0    -> ADVANCED (with caveats)
  else                         -> REJECTED

Run from backend/:  ./cryptoenv/bin/python -m research.e005_regime_book
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.foundation import load_data, SMA_LONG  # noqa: E402
from research import strategies  # noqa: E402

EXPERIMENT_ID = "E005"
HYPOTHESIS_ID = "H004"
COINS = ("bitcoin", "ethereum", "solana")
CAPITAL = 10_000.0
DEV = (200, 760)
OOS = (760, 1000)
MIN_OOS_TRADES = 5

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)


def dates_of(coin, a, b):
    daily, _, _ = load_data(coin, 365, "binance")
    ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
    f = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    return f(ts[a]), f(ts[b - 1])


def cell_stats(trades, regime):
    nets = [t["net_pct"] for t in trades if t.get("entry_regime") == regime
            and t["net_pct"] is not None]
    if not nets:
        return {"n": 0}
    return {"n": len(nets), "mean": round(sum(nets) / len(nets), 2),
            "sum": round(sum(nets), 2)}


def pooled(window_results):
    trades = [t for r in window_results for t in r["trades"]]
    nets = [t["net_pct"] for t in trades if t["net_pct"] is not None]
    wins = [x for x in nets if x > 0]
    gp, gl = sum(wins), abs(sum(x for x in nets if x <= 0))
    return {
        "trades": len(nets),
        "win_rate": round(len(wins) / len(nets), 2) if nets else None,
        "expectancy_pct": round(sum(nets) / len(nets), 3) if nets else None,
        "profit_factor": round(gp / gl, 3) if gl else (float("inf") if gp else None),
        "sum_pct": round(sum(nets), 2),
        "per_cell": {
            "BULL_RANGE(V1)": cell_stats(trades, "BULL_RANGE"),
            "BULL_TREND(S003)": cell_stats(trades, "BULL_TREND"),
        },
    }


def fmt_pooled(name, p):
    pf = "  --" if p["profit_factor"] is None else (
        " inf" if p["profit_factor"] == float("inf") else f"{p['profit_factor']:.2f}")
    exp = "  --" if p["expectancy_pct"] is None else f"{p['expectancy_pct']:+.2f}%"
    wr = "  --" if p["win_rate"] is None else f"{p['win_rate']*100:.0f}%"
    print(f"{name:<24} {p['trades']:>6}  {pf:>6}  {exp:>9}  {wr:>5}  {p['sum_pct']:>+8.2f}")


def main():
    started = datetime.now(timezone.utc)
    print("=" * 70)
    print("E005 — REGIME-CONDITIONAL BOOK (H004): DEV vs OUT-OF-SAMPLE")
    print("=" * 70)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    print(f"Started: {started.isoformat()}   Git: {commit}   Python: {platform.python_version()}")
    print("Book: V1 in BULL_RANGE | S003 in BULL_TREND | flat otherwise")
    print(f"Split: bars {DEV[0]}-{DEV[1]} dev | bars {OOS[0]}-{OOS[1]} OUT-OF-SAMPLE")
    print(f"Verdict rules: OOS trades < {MIN_OOS_TRADES} -> INCONCLUSIVE; "
          f"OOS exp > 0 -> ADVANCED; else REJECTED\n")

    results = {"dev": {}, "oos": {}, "baselines_oos": {}}
    for coin in COINS:
        d0, d1 = dates_of(coin, *DEV)
        o0, o1 = dates_of(coin, *OOS)
        print(f"--- {coin.upper()}  dev {d0}..{d1}  |  OOS {o0}..{o1} ---")
        dev = strategies.run_book(coin, source="binance", eval_from=DEV[0], eval_to=DEV[1])
        oos = strategies.run_book(coin, source="binance", eval_from=OOS[0], eval_to=OOS[1])
        v1_oos = __import__("utils.foundation", fromlist=["run"]).run(
            coin, source="binance", eval_from=OOS[0], eval_to=OOS[1])
        s3_oos = strategies.run_pullback(coin, source="binance", eval_from=OOS[0], eval_to=OOS[1])

        dd = dev.pop("rejections", None)
        od = oos.pop("rejections", None)
        print(f"  DEV  : {dev['n_trades']:>2} trades, exp {dev['expectancy_pct']:+.2f}%, "
              f"cells {dev['trigger_diag']['cand_BULL_RANGE']}R/"
              f"{dev['trigger_diag']['cand_BULL_TREND']}T")
        for t in dev["trades"]:
            print(f"      {t['entry_i']:>4}->{t['exit_i']:<4} {t['entry_regime']:<11} "
                  f"{t['reason']:<7} {t['net_pct']:+.2f}%")
        print(f"  OOS  : {oos['n_trades']:>2} trades, exp {oos['expectancy_pct']:+.2f}%, "
              f"cells {oos['trigger_diag']['cand_BULL_RANGE']}R/"
              f"{oos['trigger_diag']['cand_BULL_TREND']}T | "
              f"V1-alone OOS: {v1_oos['n_trades']} trades "
              f"({v1_oos['expectancy_pct']:+.2f}%) | S003-alone OOS: "
              f"{s3_oos['n_trades']} trades ({s3_oos['expectancy_pct']:+.2f}%)")
        results["dev"][coin] = dev
        results["oos"][coin] = oos
        results["baselines_oos"][coin] = {
            "v1": {k: v1_oos[k] for k in ("n_trades", "expectancy_pct", "profit_factor")},
            "s003": {k: s3_oos[k] for k in ("n_trades", "expectancy_pct", "profit_factor")},
        }

    print("\n--- POOLED ---")
    print(f"{'arm':<24} {'trades':>6}  {'PF':>6}  {'exp/trade':>9}  {'win%':>5}  {'sum':>9}")
    pd_, po = pooled(results["dev"].values()), pooled(results["oos"].values())
    fmt_pooled("DEV (200-760)", pd_)
    fmt_pooled("OOS (760-1000)", po)
    print(f"\nDEV cells : {pd_['per_cell']}")
    print(f"OOS cells : {po['per_cell']}")

    # ---- pre-registered verdict ----
    if po["trades"] < MIN_OOS_TRADES:
        status = "INCONCLUSIVE"
        why = (f"only {po['trades']} OOS trades (< {MIN_OOS_TRADES}): the book's "
               f"cells barely exist in the out-of-sample window — no verdict "
               f"possible, and that absence is itself the finding")
    elif po["expectancy_pct"] > 0:
        status = "ADVANCED"
        why = "OOS expectancy positive"
    else:
        status = "REJECTED"
        why = "OOS expectancy not positive"
    print(f"\nVERDICT: {status} — {why}")

    finished = datetime.now(timezone.utc)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    receipt = {
        "experiment_id": EXPERIMENT_ID, "hypothesis_id": HYPOTHESIS_ID,
        "book": "V1 in BULL_RANGE, S003 in BULL_TREND, flat otherwise (D006)",
        "split": {"dev": DEV, "oos": OOS,
                  "leak_disclosure": "E004 attribution used the full window; "
                                     "cells NOT re-selected on dev (D006 named them)",
                  "dev_dates": {c: dates_of(c, *DEV) for c in COINS},
                  "oos_dates": {c: dates_of(c, *OOS) for c in COINS}},
        "pre_registered_rules": {"min_oos_trades": MIN_OOS_TRADES,
                                 "advanced": "OOS pooled expectancy > 0"},
        "started": started.isoformat(), "finished": finished.isoformat(),
        "git_commit": commit, "python": platform.python_version(),
        "capital": CAPITAL,
        "results": results,
        "pooled_dev": pd_, "pooled_oos": po,
        "verdict": {"status": status, "reason": why},
    }
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")


if __name__ == "__main__":
    main()
