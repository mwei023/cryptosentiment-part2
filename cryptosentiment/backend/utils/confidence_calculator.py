"""Confidence scoring — no placeholders, all inputs measured.

Inputs (all real, all passed in by the caller):
- ``sentiments``: FinBERT output list with POSITIVE / NEGATIVE / NEUTRAL.
- ``price_volatility``: daily std of log returns from REAL close prices
  (see utils/volatility.py). 0.0 = flat, ~0.03-0.05 = normal crypto day,
  >= 0.08 = extreme.

Components (weights are documented heuristics, NOT calibrated
probabilities — calibration against walk-forward accuracy is roadmap
Phase 4, and the docstring says so wherever this number is shown):
- agreement (50%): 1 - std of mapped sentiment scores
  (POSITIVE=1.0, NEUTRAL=0.5, NEGATIVE=0.0). Unified headlines -> high,
  split headlines -> low. No headlines -> 0.0 contribution path.
- volatility regime (30%): ``max(0, 1 - vol / 0.08)``. An 8%+ daily
  std wipes this component to zero — correctly, because Prophet
  point forecasts are least trustworthy in wild regimes.
- sample size (20%): ``min(n / 20, 1.0)``. Fewer than 20 headlines
  means thin evidence; confidence scales down linearly.

Empty-sentiment case returns a price-only score so /predict never
crashes when NewsAPI is empty — but the ``sample_size`` term goes to
0, which visibly drags the number down instead of hiding it.
"""

import logging
import math

logger = logging.getLogger(__name__)

SAMPLE_TARGET = 20       # headlines needed for full sample-size credit
VOL_CAP = 0.08           # daily return-std that zeroes the volatility term

_SCORE_MAP = {"POSITIVE": 1.0, "NEUTRAL": 0.5, "NEGATIVE": 0.0}


def _sentiment_values(sentiments):
    vals = []
    for s in sentiments:
        label = str(s.get("label", "NEUTRAL")).upper()
        vals.append(_SCORE_MAP.get(label, 0.5))
    return vals


def calculate_volatility(scores):
    """Legacy helper: dispersion of sentiment scores in [0, 1].

    Kept for backward compatibility only. For market volatility use
    ``utils.volatility.calculate_volatility`` on PRICE data.
    """
    if not scores:
        return 0.5
    import numpy as np
    return float(min(np.std(list(scores)), 1.0))


def calculate_confidence(sentiments, volatility_score=None, price_volatility=None):
    """Compute confidence in [0, 100].

    Accepts either ``volatility_score`` (legacy name) or
    ``price_volatility`` (preferred). Must be a float >= 0 measured
    from price returns; if neither is given, defaults to 0.05
    (typical crypto day) and logs a warning so the assumption is
    visible instead of silent.
    """
    vol = price_volatility if price_volatility is not None else volatility_score
    if vol is None:
        logger.warning("No volatility passed — assuming 0.05 (typical crypto day)")
        vol = 0.05
    vol = max(0.0, float(vol))

    total = len(sentiments)
    if total == 0:
        # Price-only path: agreement contributes 0, sample contributes 0.
        vol_component = max(0.0, 1.0 - min(vol / VOL_CAP, 1.0))
        confidence = 0.3 * vol_component
        logger.info(
            f"No sentiments — price-only confidence {confidence*100:.2f}% (vol={vol:.4f})"
        )
        return round(confidence * 100, 2)

    vals = _sentiment_values(sentiments)
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    agreement = 1.0 - math.sqrt(var) * 2  # std in [0, 0.5] -> agreement in [0, 1]
    agreement = max(0.0, min(1.0, agreement))

    pos = sum(1 for s in sentiments if str(s.get("label", "")).upper() == "POSITIVE")
    neg = sum(1 for s in sentiments if str(s.get("label", "")).upper() == "NEGATIVE")
    neu = total - pos - neg
    logger.info(
        f"Sentiment: {pos}/{total} pos, {neu} neu, {neg} neg | "
        f"agreement={agreement:.2f} vol={vol:.4f}"
    )

    vol_component = max(0.0, 1.0 - min(vol / VOL_CAP, 1.0))
    sample_component = min(total / SAMPLE_TARGET, 1.0)

    confidence = (
        0.5 * agreement
        + 0.3 * vol_component
        + 0.2 * sample_component
    )
    return round(confidence * 100, 2)
