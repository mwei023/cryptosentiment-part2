# 📁 utils/sentiment_model.py
import os
from transformers import pipeline, DistilBertTokenizer, DistilBertForSequenceClassification

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../models/distilbert-base-uncased-finetuned-sst-2-english")
model_name = "distilbert-base-uncased-finetuned-sst-2-english"

# Load model and tokenizer
if not os.path.exists(MODEL_PATH):
    tokenizer = DistilBertTokenizer.from_pretrained(model_name)
    model = DistilBertForSequenceClassification.from_pretrained(model_name)
    tokenizer.save_pretrained(MODEL_PATH)
    model.save_pretrained(MODEL_PATH)

# Load from local path
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_PATH)
model = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)

sentiment_pipeline = pipeline("sentiment-analysis", model=MODEL_PATH, tokenizer=MODEL_PATH, device=-1)

def analyze_sentiment(texts):
    string_texts = [str(text) for text in texts]
    results = sentiment_pipeline(string_texts)
    return [
        {"label": res["label"], "score": res["score"], "text": text}
        for res, text in zip(results, texts)
    ]