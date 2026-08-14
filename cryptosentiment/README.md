# CryptoSentiment

**CryptoSentiment** is a cryptocurrency analysis and prediction platform that combines **market data, news sentiment analysis, and time-series forecasting** to generate short-term cryptocurrency price predictions.

The project is built around a Python/FastAPI backend and a React/TypeScript frontend, with PostgreSQL for persistence and Prophet for time-series forecasting.

> **Project status:** Active development / prototype
> This project is currently being developed as an experimental crypto analytics platform. Predictions should not be treated as financial advice.

---

## Overview

CryptoSentiment combines several data sources and analytical components:

```text
                    ┌─────────────────────┐
                    │   Cryptocurrency    │
                    │       Market        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     CoinGecko       │
                    │    Market Data      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Historical Price  │
                    │       Data          │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Prophet       │
                    │  Time-Series Model  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Price Prediction   │
                    │    + Confidence     │
                    └─────────────────────┘


       ┌──────────────────────┐
       │      NewsAPI         │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │   News Articles      │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │   DistilBERT         │
       │ Sentiment Analysis   │
       └──────────┬───────────┘
                  │
                  ▼
       ┌──────────────────────┐
       │ Sentiment Indicators │
       └──────────────────────┘
```

The long-term goal is to combine these signals into a more comprehensive cryptocurrency intelligence system.

---

# Features

### Market Data

* Cryptocurrency discovery through CoinGecko
* Historical cryptocurrency price retrieval
* Latest cryptocurrency price retrieval
* Cryptocurrency metadata
* Market rank information
* USD price conversion

### News & Sentiment

* News retrieval through NewsAPI
* Cryptocurrency-specific news searches
* DistilBERT-based sentiment classification
* Positive/negative sentiment scoring
* Local model caching

### Price Prediction

* Historical price preprocessing with Pandas
* Prophet-based time-series forecasting
* Short-term prediction horizon
* Prediction intervals
* Historical prediction storage

### Backend

* FastAPI REST API
* SQLAlchemy ORM
* PostgreSQL database
* Dependency-based database sessions
* Structured utility modules
* Celery task infrastructure

### Frontend

The frontend provides a dashboard-oriented interface for visualizing:

* Market metrics
* Predictions
* Prediction history
* News sentiment
* Confidence indicators
* Sentiment distributions
* Prediction charts

---

# Technology Stack

## Backend

| Technology   | Purpose                        |
| ------------ | ------------------------------ |
| Python       | Core backend language          |
| FastAPI      | REST API                       |
| SQLAlchemy   | ORM/database access            |
| PostgreSQL   | Persistent storage             |
| Pandas       | Data preparation               |
| Prophet      | Time-series forecasting        |
| Transformers | Sentiment analysis             |
| DistilBERT   | NLP sentiment model            |
| Requests     | Market API requests            |
| HTTPX        | Async news API requests        |
| Celery       | Background task infrastructure |
| Redis        | Celery broker                  |

## Frontend

| Technology   | Purpose            |
| ------------ | ------------------ |
| React        | UI                 |
| TypeScript   | Type safety        |
| Tailwind CSS | Styling            |
| Recharts     | Data visualization |
| Axios        | API communication  |

## External APIs

* CoinGecko — cryptocurrency market data
* NewsAPI — cryptocurrency news

---

# Architecture

```text
cryptosentiment/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── tasks.py
│   ├── celery_worker.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── crypto.py
│   │   └── prediction.py
│   │
│   ├── utils/
│   │   ├── market_data.py
│   │   ├── news_fetcher.py
│   │   ├── sentiment_analyzer.py
│   │   ├── confidence_calculator.py
│   │   ├── prediction_utils.py
│   │   └── volatility.py
│   │
│   └── models/
│       └── distilbert-base-uncased-finetuned-sst-2-english/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── utils/
│   └── ...
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Backend Architecture

The backend currently follows a relatively simple modular architecture.

```text
FastAPI
   │
   ├── API Routes
   │
   ├── Market Data
   │      └── CoinGecko
   │
   ├── News
   │      └── NewsAPI
   │
   ├── Sentiment
   │      └── DistilBERT
   │
   ├── Prediction
   │      └── Prophet
   │
   ├── Database
   │      └── PostgreSQL
   │
   └── Background Tasks
          └── Celery + Redis
```

Database configuration is centralized in `database.py`.

Models inherit from the single declarative `Base` defined in:

```text
backend/models/base.py
```

This ensures that SQLAlchemy's metadata contains all registered models when the database is initialized.

---

# Database

PostgreSQL is used for persistent application data.

The database connection is configured using the `DATABASE_URL` environment variable.

Example:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/cryptosentiment
```

The application initializes registered SQLAlchemy tables during startup.

The current prediction model stores information such as:

* Cryptocurrency
* Predicted price
* Lower prediction bound
* Upper prediction bound
* Confidence score
* Prediction type
* Generation timestamp

---

# Environment Variables

Create a `.env` file inside the `backend` directory.

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/cryptosentiment

COINGECKO_API_URL=https://api.coingecko.com/api/v3

NEWS_API_KEY=YOUR_NEWSAPI_KEY
```

### Important

Never commit `.env` to Git.

Use a safe example file instead:

```text
.env.example
```

For example:

```env
DATABASE_URL=
COINGECKO_API_URL=https://api.coingecko.com/api/v3
NEWS_API_KEY=
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/mwei023/cryptosentiment-part2.git
cd cryptosentiment-part2
```

---

## 2. Create a Python virtual environment

From the backend directory:

```bash
cd backend
python -m venv cryptoenv
```

Activate it on Linux/macOS:

```bash
source cryptoenv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

If Celery is not included in the requirements file yet:

```bash
pip install celery redis
```

---

## 4. Configure PostgreSQL

Create the database:

```bash
sudo -u postgres psql
```

Then:

```sql
CREATE DATABASE cryptosentiment;
```

Configure the database connection in `.env`.

Test the connection:

```bash
psql -h localhost -U postgres -d cryptosentiment
```

---

# Running the Backend

From:

```text
backend/
```

run:

```bash
python -m uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

OpenAPI specification:

```text
http://127.0.0.1:8000/openapi.json
```

---

# API Endpoints

The current backend exposes endpoints including:

### Root

```http
GET /
```

Checks that the API is running.

### Cryptocurrency List

```http
GET /cryptos
```

Returns available cryptocurrency assets.

### Price Prediction

```http
GET /predict/{coin_id}
```

Example:

```http
GET /predict/bitcoin
```

Generates a short-term prediction using historical market data.

### News

```http
GET /news/{coin_id}
```

Example:

```http
GET /news/solana
```

Retrieves cryptocurrency-related news.

### News Sentiment

```http
GET /analyze-news
```

Fetches news and runs sentiment analysis.

### Daily Predictions

```http
GET /trigger-daily-predictions
```

Triggers the daily prediction workflow.

> Background task execution through Celery is still being configured.

---

# Prediction Pipeline

The current prediction pipeline works approximately as follows:

```text
Coin ID
   │
   ▼
CoinGecko
   │
   ▼
Historical Prices
   │
   ▼
Pandas DataFrame
   │
   ▼
Prophet
   │
   ▼
7-Day Forecast
   │
   ├── Predicted Price
   ├── Lower Bound
   └── Upper Bound
   │
   ▼
PostgreSQL
```

The model currently uses approximately 30 days of historical price data to generate a short-term forecast.

---

# Sentiment Pipeline

News sentiment currently follows this flow:

```text
Cryptocurrency
      │
      ▼
    NewsAPI
      │
      ▼
 News Headlines
      │
      ▼
   DistilBERT
      │
      ▼
POSITIVE / NEGATIVE
      │
      ▼
Sentiment Score
```

The current sentiment model is:

```text
distilbert-base-uncased-finetuned-sst-2-english
```

This is a general-purpose English sentiment model. It is **not specifically trained on cryptocurrency news**, which is an important limitation of the current implementation.

---

# Confidence Calculation

The project contains a confidence calculation layer that is intended to combine multiple signals.

Current conceptual weighting:

```text
Sentiment             40%
Volatility             30%
Historical Trend       20%
Source Credibility     10%
```

The system is still evolving, and some components currently use placeholder values.

Therefore, the confidence score should currently be considered an experimental metric rather than a statistically calibrated probability.

---

# Background Processing

Celery is being introduced for scheduled prediction jobs.

The intended architecture is:

```text
Celery Beat
     │
     ▼
Daily Prediction Task
     │
     ▼
Crypto Assets
     │
     ├── Bitcoin
     ├── Ethereum
     ├── Solana
     └── ...
          │
          ▼
 Prediction Pipeline
          │
          ▼
      PostgreSQL
```

Redis is used as the Celery message broker.

The planned daily schedule currently runs at:

```text
00:00 UTC
```

---

# Current Development Status

## Working

* [x] FastAPI application
* [x] PostgreSQL connection
* [x] SQLAlchemy database initialization
* [x] Cryptocurrency data retrieval
* [x] Historical price retrieval
* [x] NewsAPI integration
* [x] DistilBERT sentiment analysis
* [x] Prophet prediction pipeline
* [x] Bitcoin prediction endpoint
* [x] Prediction persistence
* [x] Frontend dashboard components
* [x] Basic confidence calculation
* [x] Celery task definitions

## In Progress

* [ ] Celery/Redis environment configuration
* [ ] Automated daily prediction execution
* [ ] Production-grade confidence scoring
* [ ] Better volatility calculation
* [ ] Cryptocurrency-specific sentiment model
* [ ] Model evaluation and backtesting
* [ ] Prediction accuracy metrics
* [ ] Improved error handling
* [ ] Production deployment

---

# Known Limitations

This is an experimental system, and several parts still require significant improvement.

### 1. Prophet Training Data

The current implementation trains Prophet using a relatively small historical dataset.

This can result in unstable forecasts, particularly for highly volatile assets such as cryptocurrencies.

### 2. Cryptocurrency Sentiment

The current DistilBERT model is a general sentiment model.

Crypto-specific language such as:

```text
bullish
bearish
rekt
whale
FUD
ATH
breakout
dump
accumulation
```

may not always be interpreted correctly.

### 3. Confidence Score

The confidence calculation currently contains placeholder values for some signals.

It should eventually be replaced with a confidence model calibrated against historical prediction performance.

### 4. Prediction Accuracy

The system currently generates predictions but does not yet have a mature backtesting framework.

Future versions should measure:

* MAE
* RMSE
* MAPE
* Directional accuracy
* Prediction interval coverage
* Bull/bear classification accuracy

### 5. Financial Risk

Cryptocurrency markets are highly volatile.

Predictions generated by this project are experimental and should not be interpreted as guaranteed future prices or financial advice.

---

# Roadmap

## Phase 1 — Foundation

* [x] FastAPI backend
* [x] PostgreSQL
* [x] CoinGecko integration
* [x] NewsAPI integration
* [x] Sentiment analysis
* [x] Prophet forecasting
* [x] React dashboard

## Phase 2 — Reliability

* [ ] Proper Celery + Redis deployment
* [ ] Background prediction jobs
* [ ] API error handling
* [ ] Rate-limit handling
* [ ] Caching
* [ ] Logging improvements
* [ ] Automated tests

## Phase 3 — Intelligence

* [ ] Crypto-specific sentiment model
* [ ] Market trend indicators
* [ ] Volatility indicators
* [ ] Trading-volume signals
* [ ] Technical indicators
* [ ] Social-media sentiment
* [ ] On-chain metrics

## Phase 4 — Model Evaluation

* [ ] Historical backtesting
* [ ] Walk-forward validation
* [ ] Prediction accuracy tracking
* [ ] Model comparison
* [ ] Confidence calibration
* [ ] Automated model evaluation

## Phase 5 — Production

* [ ] Docker deployment
* [ ] Production PostgreSQL
* [ ] Redis
* [ ] Celery workers
* [ ] Celery Beat
* [ ] CI/CD
* [ ] Monitoring
* [ ] API authentication
* [ ] Rate limiting
* [ ] Production frontend deployment

---

# Future Architecture

The long-term objective is to evolve CryptoSentiment from a simple price prediction application into a multi-signal cryptocurrency intelligence platform.

```text
                    CRYPTO INTELLIGENCE
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   Market Data          News NLP          Social Data
        │                  │                  │
        ▼                  ▼                  ▼
 Technical Analysis   Sentiment Model    Sentiment Model
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    Signal Aggregator
                           │
                           ▼
                  Prediction Engine
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
          Price Forecast        Market Direction
                │                     │
                └──────────┬──────────┘
                           ▼
                    Confidence Engine
                           │
                           ▼
                    Analytics Dashboard
```

The eventual system should evaluate multiple independent signals instead of relying primarily on a single forecasting model.

---

# Development Philosophy

CryptoSentiment is being developed around a simple principle:

> **Don't just predict the price. Understand the signals driving the market.**

A useful forecasting system should combine:

* Historical price behavior
* Market momentum
* Volatility
* Trading volume
* News sentiment
* Social sentiment
* Market structure
* Model uncertainty
* Historical model performance

The goal is therefore not simply to produce a number such as:

```text
BTC → $65,000
```

but eventually something closer to:

```text
BTC
│
├── Expected price
├── Expected direction
├── Confidence
├── Sentiment
├── Volatility
├── Market momentum
├── Supporting news
├── Prediction interval
└── Historical model accuracy
```

---

# Disclaimer

CryptoSentiment is an educational and experimental software project.

Nothing generated by this application constitutes financial, investment, trading, or other professional advice.

Cryptocurrency markets are inherently risky and unpredictable. Forecasts can be wrong, sometimes substantially.

Use the project for research, experimentation, and learning—not as a guarantee of future market performance.

---

# License

License information will be added as the project matures.
