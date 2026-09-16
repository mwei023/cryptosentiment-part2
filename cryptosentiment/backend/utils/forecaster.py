"""Validated default forecaster: naive + empirical volatility bands.

Walk-forward verdict (12 folds each, live CoinGecko 365d, 1-day horizon):
- BTC: naive MAE $1,006 vs Prophet $5,270
- ETH: naive MAE $34 vs Prophet $206
- SOL: naive MAE $1.88 vs Prophet $6.63
Prophet direction = 50% (coin flip) on all three. A flattened-trend
Prophet variant scored even worse (BTC MAE $10k). Conclusion: for the
1-day horizon, "tomorrow = today" dominates. This module ships that
honestly instead of a fancier-looking worse number.

Forecast: predicted = last close.
Bands: 80% interval from recent daily log-return volatility
(last 30 closes by default):
    upper/lower = last * exp(±z80 * sigma), z80 = 1.2816
Bands are empirical, regime-aware (they widen in wild markets), and
their coverage is measured by utils/backtest.py like any other model.

Prophet is retained in prediction_utils.py as the experimental path
(use_forecaster="prophet") for research only — never the default.
"""

import math

Z80 = 1.2816  # two-sided 80% normal quantile
BAND_LOOKBACK = 30


def naive_forecast(closes, lookback: int = BAND_LOOKBACK):
    """Return (predicted, lower, upper, sigma) for next-day close.

    Raises ValueError if fewer than 10 closes (need some volatility
    history for bands to mean anything).
    """
    clean = [float(c) for c in closes if c is not None and float(c) > 0]
    if len(clean) < 10:
        raise ValueError(f"Need >= 10 closes for naive bands, got {len(clean)}.")
    last = clean[-1]
    window = clean[-(lookback + 1):] if len(clean) > lookback else clean
    log_rets = [math.log(b / a) for a, b in zip(window[:-1], window[1:]) if a > 0 and b > 0]
    if len(log_rets) < 2:
        sigma = 0.05
    else:
        mean = sum(log_rets) / len(log_rets)
        var = sum((r - mean) ** 2 for r in log_rets) / (len(log_rets) - 1)
        sigma = math.sqrt(max(var, 0.0))
    lower = last * math.exp(-Z80 * sigma)
    upper = last * math.exp(Z80 * sigma)
    return {"predicted": last, "lower": lower, "upper": upper, "sigma": sigma}
