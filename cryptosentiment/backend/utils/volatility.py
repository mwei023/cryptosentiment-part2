import numpy as np
from utils.market_data import get_historical_prices

def calculate_volatility(prices: list) -> float:
    """Calculate price volatility based on standard deviation"""
    if len(prices) < 2:
        return 0.5

    returns = np.diff(prices) / prices[:-1]
    volatility = float(np.std(returns))
    return min(volatility, 1.0)  # Cap at 1.0