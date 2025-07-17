import logging
logger = logging.getLogger(__name__)

def calculate_confidence(sentiments, volatility_score):
    """
    sentiments: list of {'label': 'POSITIVE/NEGATIVE', 'score': float}
    volatility_score: float between 0 and 1 (0 = stable, 1 = volatile)
    """
    positive_count = sum(1 for s in sentiments if s['label'] == 'POSITIVE')
    total = len(sentiments)
    sentiment_strength = positive_count / total if total > 0 else 0.5

    logger.info(f"📊 Sentiment strength: {sentiment_strength:.2f} ({positive_count}/{total} positive)")  # ✅ Now works

    # Weights
    sentiment_weight = 0.4
    volatility_weight = 0.3
    historical_trend_weight = 0.2
    source_credibility_weight = 0.1

    # Placeholder values - will be replaced later
    trend_strength = 0.7
    source_credibility = 0.8

    # Final weighted confidence score
    confidence = (
        sentiment_weight * sentiment_strength +
        volatility_weight * (1 - volatility_score) +
        historical_trend_weight * trend_strength +
        source_credibility_weight * source_credibility
    )

    return round(confidence * 100, 2)  # Return percentage

def calculate_volatility(scores):
    """
    Placeholder volatility calculator.
    Accepts a list of sentiment scores and returns a float between 0 and 1
    representing how volatile the sentiment is.
    """
    if not scores:
        return 0.5  # Neutral if no data

    # Volatility = standard deviation of sentiment scores (normalized)
    import numpy as np
    volatility = np.std(scores)
    
    # Normalize it (rough scale to [0, 1])
    return min(volatility, 1.0)
