"""Price volatility from real close prices.

Volatility = std of log returns: robust to price level, standard in
finance, comparable across BTC/ETH/SOL. Returns a daily figure;
callers map it into confidence via VOL_CAP in confidence_calculator.
"""

import math


def calculate_volatility(prices: list) -> float:
    """Std of log returns over a price series. <2 points -> 0.05
    (typical crypto day) instead of the old silent 0.5."""
    if prices is None or len(prices) < 2:
        return 0.05
    clean = [float(p) for p in prices if p is not None and float(p) > 0]
    if len(clean) < 2:
        return 0.05
    log_rets = []
    for prev, cur in zip(clean[:-1], clean[1:]):
        if prev > 0 and cur > 0:
            log_rets.append(math.log(cur / prev))
    if len(log_rets) < 2:
        return 0.05
    mean = sum(log_rets) / len(log_rets)
    var = sum((r - mean) ** 2 for r in log_rets) / (len(log_rets) - 1)
    return max(0.0, math.sqrt(var))
