"""FinBERT sentiment analysis (ProsusAI/finbert).

Why FinBERT and not the old SST-2 DistilBERT:
- SST-2 was trained on movie reviews ("this film was delightful").
  It misreads finance language: "bullish", "downgrade", "missed
  earnings", "whale accumulation", "FUD" are out-of-distribution.
- ProsusAI/finbert is BERT-base fine-tuned on financial text with
  three labels: positive / negative / neutral. Neutral matters —
  most crypto headlines are factual ("BTC holds above $60k"), and a
  binary classifier forces them into positive/negative noise.

Model cache: backend/models/finbert-prosus/ so runs don't re-download.
Lazy loading: nothing downloads at import time; the model loads on
first analyze_sentiment() call. This keeps backtests that only touch
price data fast and offline-safe.
"""

import logging
import os

logger = logging.getLogger(__name__)

MODEL_ID = "ProsusAI/finbert"
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "../models/finbert-prosus"
)

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    from transformers import pipeline

    local = MODEL_PATH if os.path.isdir(MODEL_PATH) else MODEL_ID
    logger.info(f"Loading FinBERT from {local}")
    _pipeline = pipeline(
        "sentiment-analysis",
        model=local,
        tokenizer=local,
        device=-1,  # CPU; GPU not assumed on server
        truncation=True,
        max_length=512,
    )
    return _pipeline


def download_model():
    """Pre-download + cache FinBERT locally. Run once: ``python -c
    'from utils.sentiment_analyzer import download_model; download_model()'`."""
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    os.makedirs(MODEL_PATH, exist_ok=True)
    logger.info(f"Downloading {MODEL_ID} -> {MODEL_PATH}")
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL_ID)
    tok.save_pretrained(MODEL_PATH)
    mdl.save_pretrained(MODEL_PATH)
    logger.info("FinBERT cached.")
    return MODEL_PATH


_LABEL_MAP = {
    "positive": "POSITIVE",
    "negative": "NEGATIVE",
    "neutral": "NEUTRAL",
}


def analyze_sentiment(texts):
    """Classify a list of headlines/bodies with FinBERT.

    Returns list of ``{"label": "POSITIVE"|"NEGATIVE"|"NEUTRAL",
    "score": float, "text": str}``. Empty input -> []. Non-string
    inputs are stringified; over-length inputs are truncated at 512
    tokens by the pipeline.
    """
    if not texts:
        return []
    pipe = _get_pipeline()
    string_texts = [str(t) for t in texts]
    # FinBERT pipeline handles batching; cap batch to avoid OOM on CPU
    results = pipe(string_texts, batch_size=16)
    out = []
    for res, text in zip(results, texts):
        raw = str(res.get("label", "neutral")).lower()
        out.append({
            "label": _LABEL_MAP.get(raw, "NEUTRAL"),
            "score": float(res.get("score", 0.0)),
            "text": text,
        })
    return out
