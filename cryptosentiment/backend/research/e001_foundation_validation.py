"""E001 — Foundation Validation.

Measurement harness ONLY. Per the freeze (DECISIONS D002), no strategy
code is modified here: every strategy is imported as-is and run under
identical conditions, and the receipt is persisted to research/results/E001/.

Three kinds of evidence, per the research plan:
  1. BACKWARD VALIDATION  — backtests on identical history + costs
  2. FORWARD TEST         — journal.log_today live entry (the referee)
  3. PAPER TRADE          — today's live signal with full receipt

The prediction layer (naive forecaster) gets a walk-forward receipt too,
since /predict is the product's other output.

Run from backend/:  ./cryptoenv/bin/python -m research.e001_foundation_validation
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import foundation, papertrade  # noqa: E402
from utils.backtest import validate_coin  # noqa: E402
from utils.journal import log_today, summary as journal_summary  # noqa: E402

EXPERIMENT_ID = "E001"
FOUNDATION_ID = "F001"
COINS = ("bitcoin", "ethereum", "solana")
CAPITAL = 10_000.0
HISTORY_DAYS = 365  # CoinGecko path; foundation uses 1000 Binance daily bars

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)


def _fmt(x, pct=False):
    if x is None:
        return "--"
    return f"{x:,.2f}%" if pct else f"{x:,.2f}"


def ledger_line(name, d):
    """One row of the comparison table; d is a papertrade.simulate ledger."""
    return (
        f"{name:<22} {d.get('trades', 0):>6}  "
        f"{d.get('profit_factor', float('inf')):>6.2f}  "
        f"{d.get('expectancy_pct', 0.0):>+8.2f}%  "
        f"{d.get('win_rate', 0.0) * 100:>6.1f}%  "
        f"{d.get('total_return_pct', 0.0):>+9.2f}%  "
        f"{d.get('max_drawdown_pct', 0.0):>8.2f}%"
    )


def run_backward():
    """Identical data, identical costs, all strategies. Returns results + printed table."""
    out = {}
    header = (
        f"{'strategy':<22} {'trades':>6}  {'PF':>6}  {'exp/trade':>10}  "
        f"{'win%':>6}  {'total ret':>10}  {'max DD':>8}"
    )
    for coin in COINS:
        print(f"\n=== BACKWARD: {coin.upper()} (identical closes, 0.3%/side costs) ===")
        print(header)
        res = papertrade.backtest_coin(
            coin,
            history_days=HISTORY_DAYS,
            capital=CAPITAL,
            strategies=("buy_hold", "sma_trend", "band_revert"),
        )
        for name in ("buy_hold", "sma_trend", "band_revert"):
            print(ledger_line(name, res[name]))

        # Foundation system on the SAME coin via Binance daily candles
        # (its native validation path). Not perfectly identical data to
        # CoinGecko closes — venue difference is trivial per F001 docs —
        # but same 1-day bars, same costs (0.1% fee + 0.05% slippage/side).
        fnd = foundation.run(coin, source="binance", capital=CAPITAL)
        trades = fnd.pop("trades")
        print(
            f"{'foundation (Binance)':<22} {fnd['n_trades']:>6}  "
            f"{fnd['profit_factor']:>6.2f}  {fnd['expectancy_pct']:>+8.2f}%  "
            f"{fnd['win_rate'] * 100:>6.1f}%  {fnd['total_return_pct']:>+9.2f}%  "
            f"{fnd['max_drawdown_pct']:>8.2f}%"
        )
        out[coin] = {
            "coingecko_path": {k: res[k] for k in ("buy_hold", "sma_trend", "band_revert")},
            "foundation_binance": fnd,
            "foundation_trades": trades,
        }
    return out


def run_walkforward():
    """Prediction-layer receipt: naive/prophet walk-forward on bitcoin."""
    print("\n=== FORWARD VALIDATION: /predict forecaster (bitcoin, 12 folds) ===")
    try:
        wf = validate_coin("bitcoin", history_days=365)
    except Exception as e:
        print(f"walk-forward failed: {e}")
        return {"error": str(e)}
    p, nv = wf["prophet"], wf["naive"]
    print(
        f"Prophet: MAE {_fmt(p['mae'])}  dir {p['directional_acc']:.0%}  "
        f"coverage {p['coverage']:.0%} (nominal 80%)\n"
        f"Naive:   MAE {_fmt(nv['mae'])}  (Prophet {'beats' if wf['skill']['beats_naive_mae'] else 'LOSES TO'} naive)\n"
        f"Skill:   {json.dumps(wf['skill'])}"
    )
    return {
        "prophet": p, "naive": nv, "sma7": wf["sma7"], "skill": wf["skill"],
        "n_folds": len(wf["folds"]),
    }


def run_forward_papertrade():
    """The referee: one dated journal row + settle of pending rows."""
    print("\n=== FORWARD TEST / PAPER TRADE: journal.log_today ===")
    rows = {}
    for coin in COINS:
        r = log_today(coin)
        rows[coin] = r
        if "error" in r:
            print(f"{coin}: ERROR {r['error']}")
        else:
            s = r.get("sentiment", {})
            print(
                f"{coin}: {r.get('signal', '?')}  price {r.get('price')}  "
                f"band [{r.get('band', {}).get('lower')} .. {r.get('band', {}).get('upper')}] "
                f"({r.get('band_position')})  news {s.get('n', 0)} "
                f"(+{s.get('pos', 0)}/-{s.get('neg', 0)}/={s.get('neu', 0)})  "
                f"confidence {r.get('confidence')}"
            )
    js = journal_summary()
    print(f"journal: {json.dumps(js)}")
    return {"entries": rows, "journal_summary": js}


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def main():
    started = datetime.now(timezone.utc)
    print("=" * 62)
    print("CRYPTO SENTIMENT RESEARCH ENGINE")
    print("=" * 62)
    print(f"ID:         {EXPERIMENT_ID}")
    print(f"Foundation: {FOUNDATION_ID} (frozen)")
    print(f"Started:    {started.isoformat()}")
    print(f"Git:        {git_commit()}")
    print(f"Python:     {platform.python_version()}")
    print(f"Capital:    ${CAPITAL:,.0f}   Costs: 0.1% fee + 0.05% slip per side")

    backward = run_backward()
    walkforward = run_walkforward()
    forward = run_forward_papertrade()
    finished = datetime.now(timezone.utc)

    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "foundation_id": FOUNDATION_ID,
        "started": started.isoformat(),
        "finished": finished.isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "capital": CAPITAL,
        "coins": list(COINS),
        "backward": backward,
        "walkforward": walkforward,
        "forward_papertrade": forward,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")
    print(f"Run completed:   {finished.isoformat()}")


if __name__ == "__main__":
    main()
