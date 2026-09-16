"""Foundation trading system — risk first, entries last.

The thesis: entries are decoration; survival is the strategy. Every
rule below is a textbook value (SMA200, ADX(14)/25, ATR multiples,
1% risk, 4-loss kill). NOTHING was optimized on market data, so there
is no overfit to confess to. If this fails validation, it fails
honestly and we change the thesis, not the parameters.

LONG-ONLY. One position at a time. Rules per daily bar i (all inputs
trailing-only, execution at close):

GATE (all must pass — otherwise flat, which is a position):
  1. close > SMA200 (structural uptrend; user's rule, verbatim)
  2. +DI > -DI on the slow (4-day candle) timeframe (downtrend
     momentum veto)
  3. NOT (ADX > 25 AND swing structure confirms downtrend)
     (user's rule: strong trending-down = mean-reversion suppressed)

ENTRY (only when flat, gate open, not in observation):
  close < trailing 80% lower band (oversold pullback inside an
  uptrend — the only setup this system is allowed to take).

SIZING (mathematical, regime-aware):
  risk 1% of equity per trade; hard stop 2*ATR below entry.
  coins = (0.01 * equity) / (2 * ATR_daily); notional capped at
  100% equity (no leverage), skipped if < $100 (dust).
  High volatility -> wider stop -> fewer coins. Automatic.

EXITS (asymmetric — the fix for small-wins/big-losses):
  - hard stop: entry - 2*ATR (cut losers at fixed multiple, no band-watching)
  - target: trailing upper band (mean-reversion objective)
  - trail: peak - 3*ATR ratchet (winners get room, then get kept)
  First touch on a daily close wins. Stops evaluated on closes only
  (intraday wicks ignored — a stated simplification that UNDERSTATES
  stop-outs, i.e. flatters results slightly; noted, not hidden).

KILL SWITCH: 4 consecutive losing round-trips -> 20-bar observation
mode (entries frozen, open position still managed). Counter resets
after stand-down or on any win. Consecutive losses are a regime
signal; this treats them as one.

Costs: 0.1% fee + 0.05% slippage per side, same as papertrade.py.
"""

import logging
import math
import os
import json
import time

logger = logging.getLogger(__name__)

FEE = 0.001
SLIPPAGE = 0.0005
COST_ONE_WAY = FEE + SLIPPAGE

# Textbook constants — change the thesis, not these numbers.
SMA_LONG = 200
ADX_N = 14
ADX_TREND = 25
ATR_N = 14
BAND_LOOKBACK = 30
Z80 = 1.2816
STOP_ATR = 2.0
TRAIL_ATR = 3.0
RISK_FRAC = 0.01
KILL_LOSSES = 4
KILL_STAND_DOWN = 20
MIN_NOTIONAL = 100.0
CACHE_DIR = "/tmp/foundation_cache"
CACHE_TTL = 6 * 3600


def _cache_get(name):
    try:
        p = os.path.join(CACHE_DIR, name)
        if os.path.exists(p) and time.time() - os.path.getmtime(p) < CACHE_TTL:
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _cache_put(name, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, name), "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"cache write failed: {e}")


def load_data(coin_id, history_days=365, source="coingecko"):
    """Daily closes + OHLC candles, cached 6h to respect rate limits.

    source='coingecko' (default, live path): daily closes from
      /market_chart + coarse 4-day OHLC candles (free-tier limit).
      Slow indicators run on the 4-day timeframe, ATR scaled /sqrt(4).
    source='binance' (validation path): 1000 true daily O/H/L/C
      candles (BTCUSDT etc., no key, generous limits). Slow
      indicators run on the SAME daily timeframe — strictly better,
      and the version used for all multi-regime validation below.
      Price levels differ trivially between venues; regime behavior
      doesn't. Returns (daily, candles, candle_ms).
    """
    if source == "binance":
        sym = {"bitcoin": "BTCUSDT", "ethereum": "ETHUSDT",
               "solana": "SOLUSDT"}.get(coin_id, coin_id)
        key = f"{sym}_bin1000"
        raw = _cache_get(key + ".json")
        if raw is None:
            import requests
            r = requests.get("https://api.binance.com/api/v3/klines",
                             params={"symbol": sym, "interval": "1d", "limit": 1000},
                             timeout=30)
            r.raise_for_status()
            raw = r.json()
            _cache_put(key + ".json", raw)
            time.sleep(2)
        candles = [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4])]
                   for k in raw]
        daily = [[c[0], c[4]] for c in candles]
        return daily, candles, 86400000

    from utils.market_data import get_historical_prices
    import requests
    from utils.market_data import COINGECKO_API_URL, HEADERS

    daily = _cache_get(f"{coin_id}_{history_days}_daily.json")
    if daily is None:
        data = get_historical_prices(coin_id, days=history_days)
        daily = data.get("prices", [])
        if daily:
            _cache_put(f"{coin_id}_{history_days}_daily.json", daily)
        time.sleep(6)  # free-tier courtesy gap
    candles = _cache_get(f"{coin_id}_{history_days}_4d.json")
    if candles is None:
        try:
            r = requests.get(
                f"{COINGECKO_API_URL}/coins/{coin_id}/ohlc",
                params={"vs_currency": "usd", "days": history_days},
                headers=HEADERS, timeout=30)
            r.raise_for_status()
            candles = r.json()
            _cache_put(f"{coin_id}_{history_days}_4d.json", candles)
        except Exception as e:
            logger.warning(f"OHLC fetch failed for {coin_id}: {e}")
            candles = []
        time.sleep(6)
    return daily, candles, 4 * 86400000


def gate(closes, i, candle_ctx):
    """Return (allowed: bool, reasons: dict). Candle_ctx holds the aligned
    slow-timeframe (adx, plus_di, minus_di, atr_4d) or Nones."""
    from utils.indicators import sma, downtrend_confirmed

    reasons = {}
    s200 = sma(closes, i, SMA_LONG)
    reasons["above_sma200"] = (s200 is not None and closes[i] > s200)
    adx, pdi, mdi = candle_ctx["adx"], candle_ctx["pdi"], candle_ctx["mdi"]
    reasons["plus_gt_minus"] = (pdi is not None and mdi is not None and pdi > mdi)
    struct_down = downtrend_confirmed(closes, i)
    reasons["structure_down"] = struct_down
    strong_downtrend = (adx is not None and adx > ADX_TREND and struct_down)
    reasons["strong_downtrend"] = bool(strong_downtrend)
    reasons["adx"] = round(adx, 1) if adx is not None else None
    allowed = bool(reasons["above_sma200"] and reasons["plus_gt_minus"]
                   and not strong_downtrend)
    return allowed, reasons


def run(coin_id, history_days=365, capital=10000.0, source="coingecko",
        eval_from=None, eval_to=None):
    """Full backtest. Returns ledger + trades + diagnostics.

    eval_from/eval_to: optional bar-index window for regime-split
    evaluation (indicators still warm up on all data before the
    window — no cold-start distortion, no lookahead).
    """
    from utils.indicators import sma, adx_di, atr as atr_fn

    daily, candles, candle_ms = load_data(coin_id, history_days, source)
    closes = [float(p[1]) for p in daily if p[1] and float(p[1]) > 0]
    ts = [p[0] for p in daily if p[1] and float(p[1]) > 0]
    n = len(closes)
    if n < SMA_LONG + 30:
        raise RuntimeError(f"Only {n} closes for {coin_id}; need >= {SMA_LONG + 30}.")

    # ATR timeframe scaling: Wilder ATR lives on the candle timeframe;
    # scale to daily by sqrt(time). Daily candles -> scale 1.
    atr_scale = math.sqrt(candle_ms / 86400000)
    # Precompute slow indicators per candle; align: last candle fully
    # closed before bar i (zero leakage, slight staleness — documented).
    slow = []
    for ci in range(len(candles)):
        a, p, m = adx_di(candles, ci, ADX_N)
        at = atr_fn(candles, ci, ATR_N)
        slow.append((a, p, m, at))

    def ctx_for(i):
        # Single linear pass over candles (bars advance monotonically):
        # last candle fully closed before bar i. Zero leakage.
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

    def band(i, lookback=BAND_LOOKBACK):
        # Anchored on YESTERDAY's close from the window ending yesterday:
        # a same-bar anchor on closes[i] would make "close < lower"
        # mathematically impossible. Yesterday-anchor = executable signal.
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

    cash, coins, entry, peak = capital, 0.0, 0.0, 0.0
    stop_px = tgt_px = 0.0
    entry_cost, entry_i = 0.0, 0
    consec_losses = 0
    observe_until = -1
    trades = []
    equity_curve = []
    gate_open_days = 0
    in_observation = 0
    peak_eq, max_dd = capital, 0.0

    start = SMA_LONG  # SMA200 warmup; nothing before this is tradeable
    if eval_from is not None:
        start = max(start, eval_from)
    end = n if eval_to is None else min(eval_to, n)
    for i in range(start, end):
        px = closes[i]
        ctx = ctx_for(i)
        allowed, _ = gate(closes, i, ctx)
        if allowed:
            gate_open_days += 1
        observing = i < observe_until
        if observing:
            in_observation += 1
        elif observe_until > 0 and i == observe_until:
            consec_losses = 0  # stand-down served: fresh count, per spec

        # --- manage open position (stops evaluated on close) ---
        if coins > 0:
            peak = max(peak, px)
            trail = peak - TRAIL_ATR * (ctx["atr_d"] or 0.0)
            _, upper_now = band(i)
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
                        logger.info(f"{coin_id} KILL SWITCH at bar {i}: {KILL_LOSSES} straight losses, standing down {KILL_STAND_DOWN}d")
                else:
                    consec_losses = 0

        # --- entries ---
        if coins == 0 and allowed and not observing and ctx["atr_d"]:
            lower, _ = band(i)
            if lower is not None and px < lower:
                stop_dist = STOP_ATR * ctx["atr_d"]
                if stop_dist > 0 and stop_dist / px < 0.5:  # stop < 50% away, else absurd
                    equity = cash
                    risk_budget = RISK_FRAC * equity
                    want_coins = risk_budget / stop_dist
                    cost_per_coin = px * (1 + COST_ONE_WAY)
                    max_coins = equity / cost_per_coin  # no leverage, cap 100%
                    take = min(want_coins, max_coins)
                    notional = take * cost_per_coin
                    if notional >= MIN_NOTIONAL and take > 0:
                        entry_cost = notional
                        cash -= notional
                        coins, entry, entry_i = take, px, i
                        peak = px
                        stop_px = px - stop_dist

        mtm = cash + coins * px
        equity_curve.append(mtm)
        peak_eq = max(peak_eq, mtm)
        dd = (peak_eq - mtm) / peak_eq if peak_eq else 0.0
        max_dd = max(max_dd, dd)

    if coins > 0:  # forced liquidation, same honesty rule as papertrade.py
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
        "flat_pct": round((trade_days - sum(1 for _ in iter_position_days(trades, start, end))) / trade_days * 100, 1),
    }


def iter_position_days(trades, start, n):
    held = set()
    for t in trades:
        for i in range(t["entry_i"], min(t["exit_i"] + 1, n)):
            held.add(i)
    return held
