"""Paper-trading simulator — turns system outputs into a P&L with receipts.

Rules (deliberately boring, like a real broker):
- Long-only spot, one position at a time, full-equity all-in/all-out.
  No leverage, no shorting, no margin calls to hide behind.
- Costs on EVERY fill: 0.1% exchange fee + 0.05% slippage per side,
  i.e. every round-trip starts 0.3% underwater. Strategies that can't
  clear that bar are noise, and this module will say so.
- No lookahead: every signal at day *i* may only use data up to day
  *i* (bands/SMAs are computed on trailing windows; execution is at
  day-i close — same-bar execution, the standard daily-backtest
  assumption, stated here instead of buried).
- One round-trip (buy -> sell) = one trade. Win = net positive AFTER
  costs. Forced liquidation at the last bar closes any open position
  so open trades can't flatter the stats.

Strategies:
- buy_hold: benchmark every strategy must beat. Buy day 0, sell last day.
- band_revert: the system's own bands as a mean-reversion signal —
  buy when close < trailing 80% lower band, sell when close > upper.
- sma_trend: classic 20/50 cross (sanity-check benchmark, not ours).
- sentiment_momentum: FORWARD-ONLY (needs live daily headlines; NewsAPI
  free tier has no deep history). Implemented as daily_signal_live() /
  daily_signal_dual(); it cannot be historically backtested without
  survivorship-biased news archives, and this module refuses to fake it.
  E006 compares the price-only arm against the information-enhanced
  (sentiment-gated) arm forward-only, side by side in the journal.
"""

import logging
import math

logger = logging.getLogger(__name__)

FEE = 0.001       # 0.1% per side
SLIPPAGE = 0.0005  # 0.05% per side


def _targets_buy_hold(closes):
    return [1] * len(closes)


def _trailing_sigma(closes, i, lookback=30):
    window = closes[max(0, i - lookback):i]
    if len(window) < 10:
        return None
    log_rets = [math.log(b / a) for a, b in zip(window[:-1], window[1:]) if a > 0 and b > 0]
    if len(log_rets) < 2:
        return None
    mean = sum(log_rets) / len(log_rets)
    var = sum((r - mean) ** 2 for r in log_rets) / (len(log_rets) - 1)
    return math.sqrt(max(var, 0.0))


def _targets_band_revert(closes, lookback=30):
    """1 when price is below trailing lower band (buy), 0 when above
    upper band (sell), otherwise hold previous. Starts flat."""
    targets, pos = [], 0
    for i in range(len(closes)):
        sigma = _trailing_sigma(closes, i, lookback)
        if sigma is None:
            targets.append(0)
            continue
        lower = closes[i - 1] * math.exp(-1.2816 * sigma) if i > 0 else closes[i]
        upper = closes[i - 1] * math.exp(1.2816 * sigma) if i > 0 else closes[i]
        # bands anchored on yesterday's close, evaluated against today's:
        # uses only past data, executable at today's close.
        if closes[i] < lower:
            pos = 1
        elif closes[i] > upper:
            pos = 0
        targets.append(pos)
    return targets


def _sma(values, i, n):
    w = values[max(0, i - n + 1):i + 1]
    return sum(w) / len(w) if len(w) == n else None


def _targets_sma_trend(closes, fast=20, slow=50):
    targets, pos = [], 0
    for i in range(len(closes)):
        f, s = _sma(closes, i, fast), _sma(closes, i, slow)
        if f is None or s is None:
            targets.append(0)
            continue
        pos = 1 if f > s else 0
        targets.append(pos)
    return targets


STRATEGIES = {
    "buy_hold": _targets_buy_hold,
    "band_revert": _targets_band_revert,
    "sma_trend": _targets_sma_trend,
}


def simulate(closes, targets, capital=10000.0):
    """Execute target positions at daily closes. Returns ledger dict."""
    equity = capital
    pos = 0  # 0 flat, 1 long
    entry_price = 0.0
    trades = []  # (entry, exit, gross_pct, net_pct)
    curve = []
    peak, max_dd = capital, 0.0

    for price, tgt in zip(closes, targets):
        if tgt == 1 and pos == 0:  # BUY at close incl. costs
            cost_px = price * (1 + FEE + SLIPPAGE)
            entry_price = cost_px
            pos = 1
        elif tgt == 0 and pos == 1:  # SELL
            exit_px = price * (1 - FEE - SLIPPAGE)
            gross = (price - entry_price) / entry_price
            # net: costs already in entry/exit prices
            net = (exit_px - entry_price) / entry_price
            trades.append(net)
            equity *= (1 + net)
            pos = 0
        curve.append(equity if pos == 0 else equity * (price / (entry_price / (1 + FEE + SLIPPAGE))))
        # NOTE: curve marks open position to market ex-entry-cost for readability;
        # final stats use realized equity only. Open position is force-closed below.
        peak = max(peak, curve[-1])
        dd = (peak - curve[-1]) / peak if peak else 0.0
        max_dd = max(max_dd, dd)

    if pos == 1:  # forced liquidation at last close — no free open trades
        exit_px = closes[-1] * (1 - FEE - SLIPPAGE)
        net = (exit_px - entry_price) / entry_price
        trades.append(net)
        equity *= (1 + net)

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    n = len(trades)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses)) if losses else 0.0
    total_ret = equity / capital - 1
    # Sharpe on realized trade returns is misleading for sparse trades;
    # report expectancy (per-trade edge incl. costs) as the headline.
    return {
        "trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / n if n else 0.0,
        "avg_win_pct": avg_win * 100,
        "avg_loss_pct": avg_loss * 100,
        "expectancy_pct": (sum(trades) / n * 100) if n else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0),
        "total_return_pct": total_ret * 100,
        "max_drawdown_pct": max_dd * 100,
        "final_equity": round(equity, 2),
    }


def backtest_coin(coin_id, history_days=365, capital=10000.0, strategies=("buy_hold", "band_revert", "sma_trend")):
    """Fetch real history, run all strategies, return {strategy: ledger}."""
    from utils.market_data import get_historical_prices
    data = get_historical_prices(coin_id, days=history_days)
    prices = data.get("prices", [])
    closes = [float(p[1]) for p in prices if p[1] and float(p[1]) > 0]
    if len(closes) < 60:
        raise RuntimeError(f"Only {len(closes)} closes for {coin_id}; need >= 60.")
    out = {"coin_id": coin_id, "closes": len(closes), "start": closes[0], "end": closes[-1]}
    for name in strategies:
        targets = STRATEGIES[name](closes)
        out[name] = simulate(closes, targets, capital=capital)
    return out


def gate_with_sentiment(price_signal, pos, neg):
    """E006 info-arm gate (pre-registered, zero tuned parameters).

    Price signal stands unless live FinBERT contradicts it by simple
    majority: a BUY is vetoed to HOLD when neg > pos, a SELL is vetoed
    to HOLD when pos > neg. Ties / no-news pass through untouched.
    HOLD never becomes a trade on sentiment alone — news can only
    veto, never invent, a price signal. That keeps the info arm a
    strict subset of price-arm opportunities, so any P&L difference
    is attributable to the veto, not to new entries.
    """
    if price_signal == "BUY" and neg > pos:
        return "HOLD"
    if price_signal == "SELL" and pos > neg:
        return "HOLD"
    return price_signal


def daily_signal_live(coin_id, capital=10000.0):
    """TODAY's paper-trade signal from live system outputs (forward test).

    Backward-compatible wrapper: returns the information-enhanced arm
    under the legacy keys (``signal``/``confidence``) plus both arms
    explicitly. New code should use daily_signal_dual() directly.
    """
    dual = daily_signal_dual(coin_id)
    if "error" in dual:
        return dual
    dual["signal"] = dual["signal_info"]  # legacy: enhanced arm
    dual["confidence"] = dual["conf_info"]
    return dual


def daily_signal_dual(coin_id, capital=10000.0):
    """TODAY's dual-arm signal for E006 forward test.

    Both arms share inputs (same bands, same price, same headlines).
    They differ in exactly one place — the sentiment veto:

    - price arm: signal_price from bands only,
      conf_price = confidence([], vol) — no news touched.
    - info arm:  signal_info = gate_with_sentiment(signal_price, pos, neg),
      conf_info = confidence(sentiments, vol).

    Returns dict with signal_price/signal_info/conf_price/conf_info,
    price, band position, FinBERT snapshot, and vol. Append once per
    day via journal.log_today() — that journal IS the live test.
    """
    from utils.market_data import get_historical_prices, get_latest_price
    from utils.forecaster import naive_forecast
    from utils.news_fetcher import fetch_news
    from utils.sentiment_analyzer import analyze_sentiment
    from utils.confidence_calculator import calculate_confidence
    from utils.volatility import calculate_volatility
    import asyncio

    data = get_historical_prices(coin_id, days=90)
    closes = [float(p[1]) for p in data.get("prices", []) if p[1] and float(p[1]) > 0]
    if len(closes) < 10:
        return {"coin_id": coin_id, "error": "insufficient history"}

    # Bands active for TODAY were projected from history up to yesterday:
    fc_active = naive_forecast(closes[:-1])
    # Bands active for TOMORROW projected from history up to today:
    fc_tomorrow = naive_forecast(closes)

    current_px = get_latest_price(coin_id) or closes[-1]
    band_pos = "below_lower" if current_px < fc_active["lower"] else ("above_upper" if current_px > fc_active["upper"] else "inside")
    signal = "BUY" if band_pos == "below_lower" else ("SELL" if band_pos == "above_upper" else "HOLD")

    try:
        titles = asyncio.run(fetch_news(coin_id))
    except RuntimeError:
        titles = []
    sentiments = analyze_sentiment(titles) if titles else []
    pos = sum(1 for s in sentiments if s["label"] == "POSITIVE")
    neg = sum(1 for s in sentiments if s["label"] == "NEGATIVE")
    neu = len(sentiments) - pos - neg
    vol = calculate_volatility(closes)
    conf_price = calculate_confidence([], price_volatility=vol)
    conf_info = calculate_confidence(sentiments, price_volatility=vol)
    signal_price = signal
    signal_info = gate_with_sentiment(signal_price, pos, neg)

    return {
        "coin_id": coin_id,
        "signal": signal_info,  # legacy key = info arm (backward compat)
        "signal_price": signal_price,
        "signal_info": signal_info,
        "price": current_px,
        "band": {"lower": round(fc_active["lower"], 2), "upper": round(fc_active["upper"], 2)},
        "tomorrow_band": {"lower": round(fc_tomorrow["lower"], 2), "upper": round(fc_tomorrow["upper"], 2)},
        "band_position": band_pos,
        "sentiment": {"n": len(sentiments), "pos": pos, "neu": neu, "neg": neg},
        "confidence": conf_info,  # legacy key = info arm
        "conf_price": conf_price,
        "conf_info": conf_info,
        "vol": round(vol, 6),
    }
