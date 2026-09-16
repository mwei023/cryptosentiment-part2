"""S002 — Band Reclaim (H001) for E002.

Entry-only delta vs frozen F001 (D002):
- V1-control entry (foundation.run): close < trailing lower band (knife catch).
- S002 entry (this file): yesterday closed below the lower band, TODAY
  closed back inside, and today's close broke YESTERDAY's candle high.

Everything else is byte-identical to F001: same gate (SMA200 + DI veto +
downtrend veto), same sizing (1% risk / 2xATR stop, 100% notional cap),
same exits (2xATR stop, band target, 3xATR trail), same kill switch
(4 losses -> 20-bar stand-down), same costs (0.1% fee + 0.05% slippage
per side), same forced liquidation at the last bar.

Also records a REJECTION LEDGER: every candidate bar with the exact veto
reasons, plus forward closes (fwd5/fwd10) so the counterfactual — "did
the blocked candidates go on to lose?" — can be computed later. The
forward-looking fields are ANALYSIS-ONLY: the simulation itself never
touches them.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.foundation import (  # noqa: E402
    SMA_LONG, ADX_N, ATR_N, STOP_ATR, TRAIL_ATR, RISK_FRAC,
    KILL_LOSSES, KILL_STAND_DOWN, MIN_NOTIONAL, COST_ONE_WAY,
    load_data, gate as foundation_gate,
)
from utils.indicators import adx_di, atr as atr_fn, sma  # noqa: E402

# Band constants must mirror F001 exactly (frozen — do not tune).
BAND_LOOKBACK = 30
Z80 = 1.2816


def band(closes, i, lookback=BAND_LOOKBACK):
    """Trailing 80% log-return bands anchored on YESTERDAY's close.
    Same math as foundation.run's inner band() — kept in sync by the
    freeze (D002). Returns (lower, upper) or (None, None)."""
    if i < 1:
        return None, None
    w = closes[max(0, i - lookback):i]
    if len(w) < 10:
        return None, None
    lr = [math.log(b / a) for a, b in zip(w[:-1], w[1:]) if a > 0 and b > 0]
    if len(lr) < 2:
        return None, None
    mean = sum(lr) / len(lr)
    var = sum((r - mean) ** 2 for r in lr) / (len(lr) - 1)
    sig = math.sqrt(max(var, 0.0))
    return closes[i - 1] * math.exp(-Z80 * sig), closes[i - 1] * math.exp(Z80 * sig)


def reclaim_signal(closes, high_by_ts, ts, i):
    """Single source of truth for the S002 trigger, evaluated at bar i's close.

    Conditions:
      R1: yesterday's close < lower band as of yesterday
          (band(i-1): sigma window ending at closes[i-2], anchor closes[i-2])
      R2: today's close >= lower band as of today
          (band(i): sigma window ending at closes[i-1], anchor closes[i-1])
      R3: today's close > yesterday's candle HIGH (requires OHLC)

    Returns (fired: bool, reason: str)."""
    if i < 2:
        return False, "insufficient bars"
    y_close = closes[i - 1]
    t_close = closes[i]

    lower_y, _ = band(closes, i - 1)
    if lower_y is None:
        return False, "band unavailable yesterday"
    if not (y_close < lower_y):
        return False, "R1: yesterday not below band"

    lower_t, _ = band(closes, i)
    if lower_t is None:
        return False, "band unavailable today"
    if not (t_close >= lower_t):
        return False, "R2: today still below band"

    if high_by_ts is None:
        return False, "R3: no OHLC data for candle-high break"
    y_high = high_by_ts.get(ts[i - 1])
    if y_high is None:
        return False, "R3: yesterday's candle high missing"
    if not (t_close > y_high):
        return False, "R3: candle high not broken"
    return True, ""


def pullback_signal(closes, high_by_ts, ts, i):
    """Single source of truth for the S003 trigger (H002 trend pullback),
    evaluated at bar i's close. Textbook values only (20/50 SMAs), zero
    tuned parameters.

    Conditions (all as-of-yesterday / today-close, no lookahead):
      T1: trend established — SMA20 > SMA50 as of YESTERDAY (i-1)
      T2: pullback — YESTERDAY's close < yesterday's SMA20
      T3: resume — TODAY's close >= today's SMA20
      T4: momentum — TODAY's close > yesterday's candle high (OHLC)

    Returns (fired: bool, reason: str)."""
    if i < 2:
        return False, "insufficient bars"
    y_close, t_close = closes[i - 1], closes[i]

    sma20_y = sma(closes, i - 1, 20)
    sma50_y = sma(closes, i - 1, 50)
    if sma20_y is None or sma50_y is None:
        return False, "T1: SMAs not warmed up"
    if not (sma20_y > sma50_y):
        return False, "T1: no established uptrend yesterday"
    if not (y_close < sma20_y):
        return False, "T2: yesterday not below SMA20 (no pullback)"

    sma20_t = sma(closes, i, 20)
    if not (t_close >= sma20_t):
        return False, "T3: today still below SMA20 (no resume)"

    if high_by_ts is None:
        return False, "T4: no OHLC data for momentum break"
    y_high = high_by_ts.get(ts[i - 1])
    if y_high is None:
        return False, "T4: yesterday's candle high missing"
    if not (t_close > y_high):
        return False, "T4: momentum break failed"
    return True, ""


def run_pullback(coin_id, history_days=365, capital=10000.0, source="binance",
                 eval_from=None, eval_to=None):
    """E003 arm: foundation.run twin with the S003 entry trigger.
    Non-entry logic is identical to F001 by construction (same code
    pattern as run(); gate/sizing/exits/kill copied verbatim).
    Also returns trigger/gate compatibility diagnostics."""
    daily, candles, candle_ms = load_data(coin_id, history_days, source)
    closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
    ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
    n = len(closes)
    if n < SMA_LONG + 30:
        raise RuntimeError(f"Only {n} closes for {coin_id}; need >= {SMA_LONG + 30}.")

    high_by_ts = None
    if source == "binance" and candles and len(candles) == n:
        high_by_ts = {int(c[0]): float(c[2]) for c in candles}

    atr_scale = math.sqrt(candle_ms / 86400000)
    slow = []
    for ci in range(len(candles)):
        a, p, m = adx_di(candles, ci, ADX_N)
        at = atr_fn(candles, ci, ATR_N)
        slow.append((a, p, m, at))

    def ctx_for(i):
        if not hasattr(ctx_for, "ci"):
            ctx_for.ci = 0
        while (ctx_for.ci + 1 < len(candles)
               and candles[ctx_for.ci + 1][0] + candle_ms <= ts[i]):
            ctx_for.ci += 1
        best = ctx_for.ci if candles and candles[0][0] + candle_ms <= ts[i] else None
        if best is None or slow[best][0] is None:
            return {"adx": None, "pdi": None, "mdi": None, "atr_d": None}
        a, p, m, at = slow[best]
        return {"adx": a, "pdi": p, "mdi": m,
                "atr_d": (at / atr_scale) if at else None}

    cash, coins, entry, peak = capital, 0.0, 0.0, 0.0
    stop_px = 0.0
    entry_cost, entry_i = 0.0, 0
    consec_losses = 0
    observe_until = -1
    trades = []
    rejections = []
    gate_open_days = 0
    in_observation = 0
    peak_eq, max_dd = capital, 0.0
    diag = {"fired": 0, "fired_gate_open": 0, "fired_gate_closed": 0,
            "already_in": 0, "standdown": 0, "no_atr": 0}

    start = SMA_LONG
    if eval_from is not None:
        start = max(start, eval_from)
    end = n if eval_to is None else min(eval_to, n)

    for i in range(start, end):
        px = closes[i]
        ctx = ctx_for(i)
        allowed, gate_reasons = foundation_gate(closes, i, ctx)
        if allowed:
            gate_open_days += 1
        observing = i < observe_until
        if observing:
            in_observation += 1
        elif observe_until > 0 and i == observe_until:
            consec_losses = 0

        # --- manage open position (identical to F001) ---
        if coins > 0:
            peak = max(peak, px)
            trail = peak - TRAIL_ATR * (ctx["atr_d"] or 0.0)
            _, upper_now = band(closes, i)
            hit_stop = px <= stop_px
            hit_tgt = (upper_now is not None and px >= upper_now)
            hit_trail = (ctx["atr_d"] is not None and px <= trail and px > stop_px)
            if hit_stop or hit_tgt or hit_trail:
                reason = "stop" if hit_stop else ("target" if hit_tgt else "trail")
                exit_px = px * (1 - COST_ONE_WAY)
                proceeds = coins * exit_px
                pnl = proceeds - entry_cost
                ret = pnl / entry_cost
                trades.append({"entry_i": entry_i, "exit_i": i, "reason": reason,
                               "entry": entry, "exit": px, "net_pct": ret * 100})
                cash += proceeds
                coins = 0.0
                if ret <= 0:
                    consec_losses += 1
                    if consec_losses >= KILL_LOSSES:
                        observe_until = i + KILL_STAND_DOWN
                else:
                    consec_losses = 0

        # --- candidate evaluation (records rejections + diagnostics) ---
        fired, trig_reason = pullback_signal(closes, high_by_ts, ts, i)
        if fired:
            diag["fired"] += 1
            if allowed:
                diag["fired_gate_open"] += 1
            else:
                diag["fired_gate_closed"] += 1
            if coins != 0:
                diag["already_in"] += 1
            if observing:
                diag["standdown"] += 1
            if not ctx["atr_d"]:
                diag["no_atr"] += 1
            if not (coins == 0 and allowed and not observing and ctx["atr_d"]):
                veto = {}
                if coins != 0:
                    veto["already_in_position"] = True
                if not allowed:
                    veto["gate"] = gate_reasons
                if observing:
                    veto["observation_standdown"] = True
                if not ctx["atr_d"]:
                    veto["no_atr"] = True
                rejections.append({
                    "i": i, "ts": ts[i], "close": px,
                    "trigger_reason": trig_reason, "veto": veto,
                    "fwd5": round((closes[i + 5] / px - 1) * 100, 2) if i + 5 < n else None,
                    "fwd10": round((closes[i + 10] / px - 1) * 100, 2) if i + 10 < n else None,
                })
                fired = False  # candidate blocked

        # --- entries (S003 trigger, F001 sizing) ---
        if coins == 0 and allowed and not observing and fired and ctx["atr_d"]:
            stop_dist = STOP_ATR * ctx["atr_d"]
            if stop_dist > 0 and stop_dist / px < 0.5:
                equity = cash
                risk_budget = RISK_FRAC * equity
                want_coins = risk_budget / stop_dist
                cost_per_coin = px * (1 + COST_ONE_WAY)
                max_coins = equity / cost_per_coin
                take = min(want_coins, max_coins)
                notional = take * cost_per_coin
                if notional >= MIN_NOTIONAL and take > 0:
                    entry_cost = notional
                    cash -= notional
                    coins, entry, entry_i = take, px, i
                    peak = px
                    stop_px = px - stop_dist

        mtm = cash + coins * px
        peak_eq = max(peak_eq, mtm)
        dd = (peak_eq - mtm) / peak_eq if peak_eq else 0.0
        max_dd = max(max_dd, dd)

    if coins > 0:
        exit_px = closes[end - 1] * (1 - COST_ONE_WAY)
        proceeds = coins * exit_px
        pnl = proceeds - entry_cost
        trades.append({"entry_i": entry_i, "exit_i": end - 1, "reason": "expired",
                       "entry": entry, "exit": closes[end - 1],
                       "net_pct": pnl / entry_cost * 100})
        cash += proceeds

    final = cash
    nets = [t["net_pct"] for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    gp, gl = sum(wins), abs(sum(losses))
    trade_days = end - start
    return {
        "coin_id": coin_id, "source": source, "bars": n, "trade_days": trade_days,
        "trades": trades,
        "n_trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "expectancy_pct": sum(nets) / len(nets) if nets else 0.0,
        "avg_win_pct": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss_pct": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": gp / gl if gl else (float("inf") if gp else 0.0),
        "total_return_pct": (final / capital - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
        "final_equity": round(final, 2),
        "gate_open_pct": round(gate_open_days / trade_days * 100, 1),
        "observation_pct": round(in_observation / trade_days * 100, 1),
        "n_candidates_fired": sum(1 for r in rejections if r.get("veto")) + len(trades),
        "n_rejected_after_trigger": len(rejections),
        "rejections": rejections,
        "trigger_diag": diag,
    }


def run_book(coin_id, history_days=365, capital=10000.0, source="binance",
             eval_from=None, eval_to=None):
    """E005 arm: regime-conditional book (H004, authorized by D006).

    Entry dispatch by the bar's OWN regime (trailing-only, frozen
    definitions from E004):
      BULL_RANGE -> V1 band-revert trigger (close < lower band)
      BULL_TREND -> S003 pullback trigger (pullback_signal)
      everything else -> flat (no candidates generated)
    Gates/sizing/stops/targets/trail/kill identical to F001.
    Trades carry entry_regime; diagnostics count candidates per regime.
    """
    daily, candles, candle_ms = load_data(coin_id, history_days, source)
    closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
    ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
    n = len(closes)
    if n < SMA_LONG + 30:
        raise RuntimeError(f"Only {n} closes for {coin_id}; need >= {SMA_LONG + 30}.")

    high_by_ts = None
    if source == "binance" and candles and len(candles) == n:
        high_by_ts = {int(c[0]): float(c[2]) for c in candles}

    atr_scale = math.sqrt(candle_ms / 86400000)
    slow = []
    for ci in range(len(candles)):
        a, p, m = adx_di(candles, ci, ADX_N)
        at = atr_fn(candles, ci, ATR_N)
        slow.append((a, p, m, at))

    def ctx_for(i):
        if not hasattr(ctx_for, "ci"):
            ctx_for.ci = 0
        while (ctx_for.ci + 1 < len(candles)
               and candles[ctx_for.ci + 1][0] + candle_ms <= ts[i]):
            ctx_for.ci += 1
        best = ctx_for.ci if candles and candles[0][0] + candle_ms <= ts[i] else None
        if best is None or slow[best][0] is None:
            return {"adx": None, "pdi": None, "mdi": None, "atr_d": None}
        a, p, m, at = slow[best]
        return {"adx": a, "pdi": p, "mdi": m,
                "atr_d": (at / atr_scale) if at else None}

    cash, coins, entry, peak = capital, 0.0, 0.0, 0.0
    stop_px = 0.0
    entry_cost, entry_i = 0.0, 0
    consec_losses = 0
    observe_until = -1
    trades = []
    open_rec = None
    rejections = []
    gate_open_days = 0
    in_observation = 0
    peak_eq, max_dd = capital, 0.0
    diag = {"cand_BULL_RANGE": 0, "cand_BULL_TREND": 0,
            "fired": 0, "fired_gate_open": 0, "fired_gate_closed": 0,
            "already_in": 0, "standdown": 0, "no_atr": 0}

    start = SMA_LONG
    if eval_from is not None:
        start = max(start, eval_from)
    end = n if eval_to is None else min(eval_to, n)

    for i in range(start, end):
        px = closes[i]
        ctx = ctx_for(i)
        allowed, gate_reasons = foundation_gate(closes, i, ctx)
        if allowed:
            gate_open_days += 1
        observing = i < observe_until
        if observing:
            in_observation += 1
        elif observe_until > 0 and i == observe_until:
            consec_losses = 0

        # --- manage open position (identical to F001) ---
        if coins > 0:
            peak = max(peak, px)
            trail = peak - TRAIL_ATR * (ctx["atr_d"] or 0.0)
            _, upper_now = band(closes, i)
            hit_stop = px <= stop_px
            hit_tgt = (upper_now is not None and px >= upper_now)
            hit_trail = (ctx["atr_d"] is not None and px <= trail and px > stop_px)
            if hit_stop or hit_tgt or hit_trail:
                reason = "stop" if hit_stop else ("target" if hit_tgt else "trail")
                exit_px = px * (1 - COST_ONE_WAY)
                proceeds = coins * exit_px
                pnl = proceeds - entry_cost
                ret = pnl / entry_cost
                open_rec.update({"exit_i": i, "reason": reason, "exit": px,
                                 "net_pct": ret * 100})
                trades.append(open_rec)
                open_rec = None
                cash += proceeds
                coins = 0.0
                if ret <= 0:
                    consec_losses += 1
                    if consec_losses >= KILL_LOSSES:
                        observe_until = i + KILL_STAND_DOWN
                else:
                    consec_losses = 0

        # --- regime of THIS bar (trailing-only) ---
        s200 = sma(closes, i, SMA_LONG)
        bull = s200 is not None and px > s200
        trending = ctx["adx"] is not None and ctx["adx"] >= 25
        regime = f"{'BULL' if bull else 'BEAR'}_{'TREND' if trending else 'RANGE'}"

        # --- candidate dispatch (the book) ---
        if regime == "BULL_RANGE":
            lower_i, _ = band(closes, i)
            if lower_i is not None and px < lower_i:
                fired, trig_reason = True, "V1: close below lower band"
            else:
                fired, trig_reason = False, "no V1 trigger"
        elif regime == "BULL_TREND":
            fired, trig_reason = pullback_signal(closes, high_by_ts, ts, i)
        else:
            fired, trig_reason = False, f"book is flat in {regime}"

        if fired:
            diag["fired"] += 1
            diag[f"cand_{regime}"] = diag.get(f"cand_{regime}", 0) + 1
            if allowed:
                diag["fired_gate_open"] += 1
            else:
                diag["fired_gate_closed"] += 1
            if coins != 0:
                diag["already_in"] += 1
            if observing:
                diag["standdown"] += 1
            if not ctx["atr_d"]:
                diag["no_atr"] += 1
            if not (coins == 0 and allowed and not observing and ctx["atr_d"]):
                veto = {}
                if coins != 0:
                    veto["already_in_position"] = True
                if not allowed:
                    veto["gate"] = gate_reasons
                if observing:
                    veto["observation_standdown"] = True
                if not ctx["atr_d"]:
                    veto["no_atr"] = True
                rejections.append({
                    "i": i, "ts": ts[i], "close": px, "regime": regime,
                    "trigger_reason": trig_reason, "veto": veto,
                    "fwd5": round((closes[i + 5] / px - 1) * 100, 2) if i + 5 < n else None,
                    "fwd10": round((closes[i + 10] / px - 1) * 100, 2) if i + 10 < n else None,
                })
                fired = False

        # --- entries (book trigger, F001 sizing) ---
        if coins == 0 and allowed and not observing and fired and ctx["atr_d"]:
            stop_dist = STOP_ATR * ctx["atr_d"]
            if stop_dist > 0 and stop_dist / px < 0.5:
                equity = cash
                risk_budget = RISK_FRAC * equity
                want_coins = risk_budget / stop_dist
                cost_per_coin = px * (1 + COST_ONE_WAY)
                max_coins = equity / cost_per_coin
                take = min(want_coins, max_coins)
                notional = take * cost_per_coin
                if notional >= MIN_NOTIONAL and take > 0:
                    entry_cost = notional
                    cash -= notional
                    coins, entry, entry_i = take, px, i
                    peak = px
                    stop_px = px - stop_dist
                    open_rec = {"entry_i": i, "exit_i": None,
                                "reason": "open", "entry": px, "exit": None,
                                "net_pct": None, "entry_regime": regime}

        mtm = cash + coins * px
        peak_eq = max(peak_eq, mtm)
        dd = (peak_eq - mtm) / peak_eq if peak_eq else 0.0
        max_dd = max(max_dd, dd)

    if open_rec is not None:  # forced liquidation at the last bar
        exit_px = closes[end - 1] * (1 - COST_ONE_WAY)
        pnl = coins * exit_px - entry_cost
        open_rec.update({"exit_i": end - 1, "reason": "expired",
                         "exit": closes[end - 1],
                         "net_pct": pnl / entry_cost * 100})
        trades.append(open_rec)
        cash += coins * exit_px
        coins = 0.0

    final = cash
    nets = [t["net_pct"] for t in trades if t["net_pct"] is not None]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    gp, gl = sum(wins), abs(sum(losses))
    trade_days = end - start
    return {
        "coin_id": coin_id, "source": source, "bars": n, "trade_days": trade_days,
        "trades": trades, "n_trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "expectancy_pct": sum(nets) / len(nets) if nets else 0.0,
        "avg_win_pct": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss_pct": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": gp / gl if gl else (float("inf") if gp else 0.0),
        "total_return_pct": (final / capital - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
        "final_equity": round(final, 2),
        "gate_open_pct": round(gate_open_days / trade_days * 100, 1),
        "observation_pct": round(in_observation / trade_days * 100, 1),
        "n_rejected_after_trigger": len(rejections),
        "rejections": rejections,
        "trigger_diag": diag,
    }


def run(coin_id, history_days=365, capital=10000.0, source="binance",
        eval_from=None, eval_to=None):
    """Head-to-head twin of foundation.run with the S002 entry trigger.
    Non-entry logic is identical by construction (copied from F001)."""
    daily, candles, candle_ms = load_data(coin_id, history_days, source)
    closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
    ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
    n = len(closes)
    if n < SMA_LONG + 30:
        raise RuntimeError(f"Only {n} closes for {coin_id}; need >= {SMA_LONG + 30}.")

    # Binance path: candles ARE daily [ts, o, h, l, c] — index-aligned with
    # daily closes. Needed for R3 (yesterday's high). Elsewhere: None.
    high_by_ts = None
    if source == "binance" and candles and len(candles) == n:
        high_by_ts = {int(c[0]): float(c[2]) for c in candles}

    # Slow indicators on the candle timeframe, aligned like F001.
    atr_scale = math.sqrt(candle_ms / 86400000)
    slow = []
    for ci in range(len(candles)):
        a, p, m = adx_di(candles, ci, ADX_N)
        at = atr_fn(candles, ci, ATR_N)
        slow.append((a, p, m, at))

    def ctx_for(i):
        if not hasattr(ctx_for, "ci"):
            ctx_for.ci = 0
        while (ctx_for.ci + 1 < len(candles)
               and candles[ctx_for.ci + 1][0] + candle_ms <= ts[i]):
            ctx_for.ci += 1
        best = ctx_for.ci if candles and candles[0][0] + candle_ms <= ts[i] else None
        if best is None or slow[best][0] is None:
            return {"adx": None, "pdi": None, "mdi": None, "atr_d": None}
        a, p, m, at = slow[best]
        return {"adx": a, "pdi": p, "mdi": m,
                "atr_d": (at / atr_scale) if at else None}

    cash, coins, entry, peak = capital, 0.0, 0.0, 0.0
    stop_px = 0.0
    entry_cost, entry_i = 0.0, 0
    consec_losses = 0
    observe_until = -1
    trades = []
    rejections = []
    gate_open_days = 0
    in_observation = 0
    peak_eq, max_dd = capital, 0.0

    start = SMA_LONG
    if eval_from is not None:
        start = max(start, eval_from)
    end = n if eval_to is None else min(eval_to, n)

    for i in range(start, end):
        px = closes[i]
        ctx = ctx_for(i)
        allowed, gate_reasons = foundation_gate(closes, i, ctx)
        if allowed:
            gate_open_days += 1
        observing = i < observe_until
        if observing:
            in_observation += 1
        elif observe_until > 0 and i == observe_until:
            consec_losses = 0

        # --- manage open position (identical to F001) ---
        if coins > 0:
            peak = max(peak, px)
            trail = peak - TRAIL_ATR * (ctx["atr_d"] or 0.0)
            _, upper_now = band(closes, i)
            hit_stop = px <= stop_px
            hit_tgt = (upper_now is not None and px >= upper_now)
            hit_trail = (ctx["atr_d"] is not None and px <= trail and px > stop_px)
            if hit_stop or hit_tgt or hit_trail:
                reason = "stop" if hit_stop else ("target" if hit_tgt else "trail")
                exit_px = px * (1 - COST_ONE_WAY)
                proceeds = coins * exit_px
                pnl = proceeds - entry_cost
                ret = pnl / entry_cost
                trades.append({"entry_i": entry_i, "exit_i": i, "reason": reason,
                               "entry": entry, "exit": px, "net_pct": ret * 100})
                cash += proceeds
                coins = 0.0
                if ret <= 0:
                    consec_losses += 1
                    if consec_losses >= KILL_LOSSES:
                        observe_until = i + KILL_STAND_DOWN
                else:
                    consec_losses = 0

        # --- candidate evaluation (records rejections) ---
        fired, trig_reason = reclaim_signal(closes, high_by_ts, ts, i)
        lower_i, _ = band(closes, i)
        v1_would = (lower_i is not None and px < lower_i)  # V1 knife-catch trigger
        if fired and not (coins == 0 and allowed and not observing and ctx["atr_d"]):
            veto = {}
            if coins != 0:
                veto["already_in_position"] = True
            if not allowed:
                veto["gate"] = gate_reasons
            if observing:
                veto["observation_standdown"] = True
            if not ctx["atr_d"]:
                veto["no_atr"] = True
            rejections.append({
                "i": i, "ts": ts[i], "close": px, "trigger": fired,
                "trigger_reason": trig_reason, "veto": veto,
                "v1_would_enter": bool(v1_would),
                "fwd5": round((closes[i + 5] / px - 1) * 100, 2) if i + 5 < n else None,
                "fwd10": round((closes[i + 10] / px - 1) * 100, 2) if i + 10 < n else None,
            })
            fired = False  # candidate blocked

        # --- entries (S002 trigger, F001 sizing) ---
        if coins == 0 and allowed and not observing and fired and ctx["atr_d"]:
            stop_dist = STOP_ATR * ctx["atr_d"]
            if stop_dist > 0 and stop_dist / px < 0.5:
                equity = cash
                risk_budget = RISK_FRAC * equity
                want_coins = risk_budget / stop_dist
                cost_per_coin = px * (1 + COST_ONE_WAY)
                max_coins = equity / cost_per_coin
                take = min(want_coins, max_coins)
                notional = take * cost_per_coin
                if notional >= MIN_NOTIONAL and take > 0:
                    entry_cost = notional
                    cash -= notional
                    coins, entry, entry_i = take, px, i
                    peak = px
                    stop_px = px - stop_dist

        mtm = cash + coins * px
        peak_eq = max(peak_eq, mtm)
        dd = (peak_eq - mtm) / peak_eq if peak_eq else 0.0
        max_dd = max(max_dd, dd)

    if coins > 0:
        exit_px = closes[end - 1] * (1 - COST_ONE_WAY)
        proceeds = coins * exit_px
        pnl = proceeds - entry_cost
        trades.append({"entry_i": entry_i, "exit_i": end - 1, "reason": "expired",
                       "entry": entry, "exit": closes[end - 1],
                       "net_pct": pnl / entry_cost * 100})
        cash += proceeds

    final = cash
    nets = [t["net_pct"] for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    gp, gl = sum(wins), abs(sum(losses))
    trade_days = end - start
    return {
        "coin_id": coin_id, "source": source, "bars": n, "trade_days": trade_days,
        "trades": trades,
        "n_trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "expectancy_pct": sum(nets) / len(nets) if nets else 0.0,
        "avg_win_pct": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss_pct": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": gp / gl if gl else (float("inf") if gp else 0.0),
        "total_return_pct": (final / capital - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
        "final_equity": round(final, 2),
        "gate_open_pct": round(gate_open_days / trade_days * 100, 1),
        "observation_pct": round(in_observation / trade_days * 100, 1),
        "n_candidates_fired": sum(1 for r in rejections if r["trigger"]) + len(trades),
        "n_rejected_after_trigger": sum(1 for r in rejections if r["trigger"]),
        "rejections": rejections,
    }
