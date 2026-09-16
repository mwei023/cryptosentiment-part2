"""E004 — Regime Attribution of Existing Ledgers.

No new hypothesis. Slices the trade and rejection ledgers of E001-E003
by regime to locate where edge lives or dies. Tests the suspicion
recorded in D005: "SOL chop is the killer; BTC/ETH trend is where any
edge lives."

REGIME DEFINITIONS (pre-registered before running; reuse frozen F001
constants wherever possible — no new tuning):
  Trend axis (both computed as-of the bar, trailing only):
    BULL  = close > SMA200            (F001's own structural rule)
    BEAR  = close <= SMA200
    TREND = ADX(14) >= 25             (F001's own threshold)
    RANGE = ADX(14) < 25
  -> four buckets: BULL_TREND, BULL_RANGE, BEAR_TREND, BEAR_RANGE
  Volatility overlay (orthogonal binary flag):
    HIGH_VOL = trailing 30d return sigma > 1.5 x its own trailing 252d
    median (backward-looking window; zero invented constants)
Assignment: trades by regime at ENTRY bar; blocked candidates by regime
at their bar, judged on fwd10.

DECISION RULE (pre-registered): if BULL_TREND expectancy is positive
while BEAR/HIGH_VOL is materially negative, D006 proposes a regime/
volatility filter as a D-level change superseding part of D002's freeze
— not another entry hypothesis.

Run from backend/:  ./cryptoenv/bin/python -m research.e004_regime_attribution
"""

import json
import math
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.foundation import SMA_LONG, load_data  # noqa: E402
from utils.indicators import sma, adx_di  # noqa: E402
from research import strategies  # noqa: E402
from research.strategies import band  # noqa: E402

EXPERIMENT_ID = "E004"
FOUNDATION_ID = "F001"
COINS = ("bitcoin", "ethereum", "solana")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", EXPERIMENT_ID)

ADX_TREND = 25       # F001's own threshold (frozen)
VOL_LOOKBACK = 30    # matches the frozen band window
VOL_MEDIAN_WINDOW = 252
VOL_MULT = 1.5

SYSTEMS = {
    "S001_V1_band_revert": "foundation_v1",
    "S002_band_reclaim": "s002",
    "S003_trend_pullback": "s003",
}


def trailing_sigma(closes, i):
    if i < VOL_LOOKBACK:
        return None
    w = closes[i - VOL_LOOKBACK:i]
    lr = [math.log(b / a) for a, b in zip(w[:-1], w[1:]) if a > 0 and b > 0]
    if len(lr) < 2:
        return None
    m = sum(lr) / len(lr)
    var = sum((x - m) ** 2 for x in lr) / (len(lr) - 1)
    return math.sqrt(max(var, 0.0))


def trailing_median(vals):
    s = sorted(v for v in vals if v is not None)
    if not s:
        return None
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def regime_of(closes, adx_at_i, i, sigmas):
    """4-bucket trend regime + orthogonal high-vol flag at bar i."""
    s200 = sma(closes, i, SMA_LONG)
    bull = s200 is not None and closes[i] > s200
    trending = adx_at_i is not None and adx_at_i >= ADX_TREND
    regime = f"{'BULL' if bull else 'BEAR'}_{'TREND' if trending else 'RANGE'}"
    sig = sigmas[i]
    med = trailing_median(sigmas[max(0, i - VOL_MEDIAN_WINDOW):i])
    high_vol = bool(sig is not None and med is not None and sig > VOL_MULT * med)
    return regime, high_vol


def adx_series(candles, candle_ms, ts):
    """ADX at each daily bar (last fully-closed candle alignment, as F001)."""
    atr_scale = math.sqrt(candle_ms / 86400000) if candle_ms else 1.0
    slow = []
    for ci in range(len(candles)):
        a, p, m = adx_di(candles, ci, 14)
        slow.append(a)
    out, cursor = [], 0
    for i in range(len(ts)):
        while (cursor + 1 < len(candles)
               and candles[cursor + 1][0] + candle_ms <= ts[i]):
            cursor += 1
        ok = candles and candles[0][0] + candle_ms <= ts[i]
        out.append(slow[cursor] if ok and cursor < len(slow) else None)
    return out


def collect():
    """Regenerate all ledgers (same code paths as E001-E003 runs)."""
    ledgers = {"trades": [], "candidates": []}
    for coin in COINS:
        daily, candles, candle_ms = load_data(coin, 365, "binance")
        closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
        ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
        n = len(closes)
        high_by_ts = {int(c[0]): float(c[2]) for c in candles}
        adxs = adx_series(candles, candle_ms, ts)
        sigmas = [trailing_sigma(closes, i) for i in range(n)]

        # S001 V1 (control entries) — trades only
        v1 = strategies  # placeholder to keep flake quiet; replaced below
        from utils import foundation
        r = foundation.run(coin, source="binance")
        for t in r["trades"]:
            reg, hv = regime_of(closes, adxs[t["entry_i"]], t["entry_i"], sigmas)
            ledgers["trades"].append({
                "system": "S001_V1_band_revert", "coin": coin,
                "entry_i": t["entry_i"], "net_pct": t["net_pct"],
                "reason": t["reason"], "regime": reg, "high_vol": hv,
            })

        # S002 + S003 ledgers
        s2 = strategies.run(coin, source="binance")
        for t in s2["trades"]:
            reg, hv = regime_of(closes, adxs[t["entry_i"]], t["entry_i"], sigmas)
            ledgers["trades"].append({
                "system": "S002_band_reclaim", "coin": coin,
                "entry_i": t["entry_i"], "net_pct": t["net_pct"],
                "reason": t["reason"], "regime": reg, "high_vol": hv,
            })
        for rj in s2["rejections"]:
            if rj.get("fwd10") is None:
                continue
            reg, hv = regime_of(closes, adxs[rj["i"]], rj["i"], sigmas)
            ledgers["candidates"].append({
                "system": "S002_band_reclaim", "coin": coin,
                "i": rj["i"], "fwd10": rj["fwd10"],
                "regime": reg, "high_vol": hv,
            })

        s3 = strategies.run_pullback(coin, source="binance")
        for t in s3["trades"]:
            reg, hv = regime_of(closes, adxs[t["entry_i"]], t["entry_i"], sigmas)
            ledgers["trades"].append({
                "system": "S003_trend_pullback", "coin": coin,
                "entry_i": t["entry_i"], "net_pct": t["net_pct"],
                "reason": t["reason"], "regime": reg, "high_vol": hv,
            })
        for rj in s3["rejections"]:
            if rj.get("fwd10") is None:
                continue
            reg, hv = regime_of(closes, adxs[rj["i"]], rj["i"], sigmas)
            ledgers["candidates"].append({
                "system": "S003_trend_pullback", "coin": coin,
                "i": rj["i"], "fwd10": rj["fwd10"],
                "regime": reg, "high_vol": hv,
            })
        del high_by_ts  # only daily closes/ADX needed for regime labels
    return ledgers


def slice_table(rows, value_key):
    """Aggregate rows by regime; value_key = 'net_pct' or 'fwd10'."""
    buckets = {}
    for r in rows:
        buckets.setdefault(r["regime"], []).append(r[value_key])
    out = {}
    order = ["BULL_TREND", "BULL_RANGE", "BEAR_TREND", "BEAR_RANGE"]
    for k in order + [k for k in buckets if k not in order]:
        v = buckets.get(k)
        if not v:
            out[k] = {"n": 0}
            continue
        up = sum(1 for x in v if x > 0)
        out[k] = {
            "n": len(v),
            "mean_pct": round(sum(v) / len(v), 2),
            "median_pct": round(sorted(v)[len(v) // 2], 2),
            "win_rate": round(up / len(v), 2),
            "sum_pct": round(sum(v), 2),
        }
    return out


def vol_slice(rows, value_key):
    buckets = {"HIGH_VOL": [], "NORMAL_VOL": []}
    for r in rows:
        buckets["HIGH_VOL" if r["high_vol"] else "NORMAL_VOL"].append(r[value_key])
    return {k: {
        "n": len(v),
        "mean_pct": round(sum(v) / len(v), 2) if v else None,
        "median_pct": round(sorted(v)[len(v) // 2], 2) if v else None,
        "win_rate": round(sum(1 for x in v if x > 0) / len(v), 2) if v else None,
        "sum_pct": round(sum(v), 2) if v else None,
    } for k, v in buckets.items()}


def print_table(title, table):
    print(f"\n--- {title} ---")
    print(f"{'regime':<12} {'n':>5}  {'mean':>8}  {'median':>8}  {'win%':>6}  {'sum':>9}")
    for k, v in table.items():
        if v.get("n", 0) == 0 or v.get("mean_pct") is None:
            print(f"{k:<12} {v.get('n', 0):>5}  {'--':>8}  {'--':>8}  {'--':>6}  {'--':>9}")
            continue
        print(f"{k:<12} {v['n']:>5}  {v['mean_pct']:>+8.2f}  {v['median_pct']:>+8.2f}  "
              f"{v['win_rate']*100:>5.0f}%  {v['sum_pct']:>+9.2f}")


def main():
    started = datetime.now(timezone.utc)
    print("=" * 70)
    print("E004 — REGIME ATTRIBUTION OF E001–E003 LEDGERS")
    print("=" * 70)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    print(f"Started: {started.isoformat()}   Git: {commit}   Python: {platform.python_version()}")
    print("Regimes (pre-registered): BULL/BEAR = close vs SMA200; "
          "TREND/RANGE = ADX14 25; HIGH_VOL = sigma30 > 1.5x median252\n")

    ledgers = collect()
    trades, cands = ledgers["trades"], ledgers["candidates"]

    # ---- trades by regime, per system and pooled ----
    for system in SYSTEMS:
        rows = [t for t in trades if t["system"] == system]
        print_table(f"TRADES — {system} ({len(rows)} trades)",
                    slice_table(rows, "net_pct"))
    print_table(f"TRADES — POOLED ({len(trades)} trades)",
                slice_table(trades, "net_pct"))

    # ---- volatility overlay on pooled trades ----
    print_table("TRADES — POOLED by volatility flag", vol_slice(trades, "net_pct"))

    # ---- blocked candidates by regime (counterfactual quality of gate) ----
    print_table(f"BLOCKED CANDIDATES — pooled fwd10 ({len(cands)})",
                slice_table(cands, "fwd10"))
    print_table("BLOCKED CANDIDATES — by volatility flag",
                vol_slice(cands, "fwd10"))

    # ---- the pre-registered question ----
    pooled = slice_table(trades, "net_pct")
    bt = pooled.get("BULL_TREND", {})
    br = pooled.get("BEAR_RANGE", {})
    hv = vol_slice(trades, "net_pct").get("HIGH_VOL", {})
    print("\n--- PRE-REGISTERED DECISION RULE ---")
    print(f"BULL_TREND: n={bt.get('n', 0)}, mean={bt.get('mean_pct', '--')}%")
    print(f"BEAR_RANGE: n={br.get('n', 0)}, mean={br.get('mean_pct', '--')}%")
    print(f"HIGH_VOL:   n={hv.get('n', 0)}, mean={hv.get('mean_pct', '--')}%")

    bt_positive = bt.get("n", 0) > 0 and bt.get("mean_pct", 0) > 0
    bear_or_hv_negative = ((br.get("n", 0) > 0 and br.get("mean_pct", 0) < 0)
                           or (hv.get("n", 0) > 0 and hv.get("mean_pct", 0) < 0))
    if bt_positive and bear_or_hv_negative:
        print("=> BULL_TREND positive AND BEAR/HIGH_VOL negative: D006 = "
              "regime/volatility filter at the D-level (supersedes part of D002).")
        verdict = {"status": "CONFIRMED_CHOP_KILLER",
                   "d006": "REGIME/VOL FILTER PROPOSED"}
    elif not any(v.get("n", 0) for v in pooled.values()):
        verdict = {"status": "NO_DATA", "d006": "NONE"}
    else:
        print("=> Pattern NOT confirmed; no D006 filter proposal from this run.")
        verdict = {"status": "PATTERN_NOT_CONFIRMED", "d006": "NONE"}

    finished = datetime.now(timezone.utc)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "type": "analysis_of_existing_ledgers",
        "started": started.isoformat(), "finished": finished.isoformat(),
        "git_commit": commit, "python": platform.python_version(),
        "regime_definitions": {
            "bull_bear": "close vs SMA200 (F001 rule)",
            "trend_range": "ADX(14) >= 25 (F001 threshold)",
            "high_vol": "trailing 30d sigma > 1.5x trailing 252d median",
            "assignment": "trades by entry-bar regime; candidates by bar, judged fwd10",
        },
        "ledgers": ledgers,
        "tables": {
            "trades_by_system": {s: slice_table(
                [t for t in trades if t["system"] == s], "net_pct") for s in SYSTEMS},
            "trades_pooled": slice_table(trades, "net_pct"),
            "trades_vol": vol_slice(trades, "net_pct"),
            "candidates_pooled_fwd10": slice_table(cands, "fwd10"),
            "candidates_vol": vol_slice(cands, "fwd10"),
        },
        "verdict": verdict,
    }
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(receipt, f, indent=2, default=str)
    print(f"\nReceipt written: research/results/{EXPERIMENT_ID}/summary.json")


if __name__ == "__main__":
    main()
