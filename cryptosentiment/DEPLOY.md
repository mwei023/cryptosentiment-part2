# Deploying CryptoSentiment to Render — $0 topology

## Architecture

```
GitHub repo
 ├── push (main) ──────────────► Render auto-deploy
 │     ├── cryptosentiment-api       (free web service, Python 3.11, 512 MB)
 │     ├── cryptosentiment-frontend  (free static site, CRA build)
 │     └── cryptosentiment-db        (free Postgres 16)
 └── schedule 00:05 UTC ──────► GitHub Actions: daily-journal workflow
       runs research/daily_report.py (with FinBERT — 7 GB runner RAM),
       commits paper_journal.csv + daily_reports/<date>.json, pushes.
       That push triggers the Render auto-deploy above, so the API
       serves fresh /research/* data from the committed files.
```

**Why the journal runs on GitHub Actions, not Render:** Render has no free
tier for background workers (Celery), and free web services cannot mount
persistent disks — the journal CSV would be wiped on every deploy/restart.
The repo itself is the persistence layer; the API reads the committed files.

**Why FinBERT is off on the API:** the free web tier has 512 MB RAM;
torch + BERT-base needs ~1–2 GB. `DISABLE_HEAVY_MODELS=1` (set in
render.yaml) makes `/analyze-news`, `/news/{coin}` and `/confidence/{coin}`
return 503 and makes `/predict` compute confidence from price data only.
The journal job on GitHub Actions runs the full model fine (7 GB runners).

Everything else works on free: `/cryptos`, `/prices/{coin}`, `/history/{coin}`,
`/predict/{coin}` (naive forecaster), and all `/research/*` endpoints.

## One-time setup

1. **Push this repo to GitHub** (the workflow file is at
   `.github/workflows/daily-journal.yml`, relative to repo root).

2. **Add the NewsAPI secret** for the journal job:
   `gh secret set NEWS_API_KEY` (or Settings → Secrets and variables →
   Actions). Optional — without it the info arm logs price-only rows.

3. **Create the Render resources.** Either:
   - **Blueprint** (recommended): Render dashboard → New → Blueprint,
     point it at the repo. It reads `cryptosentiment/render.yaml`… note the
     blueprint lives in a subdirectory, so set the **Root Directory** to
     `cryptosentiment` when creating the blueprint, or
   - **Manual**: create the three services with the settings from
     `cryptosentiment/render.yaml` (rootDir `backend` for the API,
     `frontend` for the static site; sync `NEWS_API_KEY` in the dashboard).

4. **Verify env wiring after first deploy:**
   - API → Environment: `DATABASE_URL` should be auto-linked from the
     database; `CORS_EXTRA_ORIGINS` must match the actual frontend URL
     (Render names the URL after the service — if your services aren't
     named `cryptosentiment-api`/`cryptosentiment-frontend`, update the
     values in render.yaml and in the frontend's `REACT_APP_API_URL`).
   - Frontend → Environment: `REACT_APP_API_URL` = the API's URL
     (build-time variable — redeploy the frontend after changing it).

5. **Smoke test:**
   ```bash
   curl https://<api-url>/health || curl https://<api-url>/
   curl https://<api-url>/research/scoreboard
   curl "https://<api-url>/prices/bitcoin?days=7"
   curl -I https://<api-url>/analyze-news        # expect 503 on free tier
   ```

## The daily loop (what "running the experiment" means now)

| Time (UTC) | What | Where |
|---|---|---|
| 00:05 | GitHub Actions runs the E006 journal (settle + log + report, commits results) | Actions |
| ~00:10 | Push triggers Render auto-deploy; API serves the new data | Render |
| anytime | Read the latest state: `/research/daily-report`, `/research/scoreboard`, `/research/journal` | API |

Manual re-run after CoinGecko rate-limit flakiness: Actions → daily-journal
→ Run workflow (idempotent per day; it will fill in any coins that failed).

Local runs work exactly as before:
```bash
cd cryptosentiment/backend && ./cryptoenv/bin/python -m research.daily_report
```

## Costs

| Resource | Plan | $ |
|---|---|---|
| API web service | free (512 MB, spins down when idle) | 0 |
| Frontend static site | free | 0 |
| Postgres | free (expires after 30 days — see caveats) | 0 |
| Celery + Redis | replaced by GitHub Actions + repo files | 0 |
| GitHub Actions (public repo) | free tier | 0 |

## Caveats & upgrade path

- **Free web services spin down after ~15 min idle** — first request after
  that takes ~30–60 s (cold start). Frontend users will notice.
- **Free Postgres databases expire after 30 days** on Render's free tier.
  The app re-creates tables on boot, but stored predictions
  (`/history/{coin}`) are lost unless upgraded. The E006 journal is immune
  (it lives in git, not Postgres).
- **`/predict` on the free tier uses price-only confidence** (news/FinBERT
  skipped) and only the default `naive` forecaster — `forecaster=prophet`
  will still work but is the experimental path.
- **Upgrade to enable FinBERT on the API**: bump the API to a paid Starter
  instance (512 MB → 512 MB+RAM tiers: pick one with ≥1 GB), remove
  `DISABLE_HEAVY_MODELS` from the API's env, and switch the build command
  to `pip install -r requirements.txt`.
- **Task queue (`/trigger-daily-predictions`)** is not available on this
  topology (no Celery worker). The endpoint returns 503. The daily journal
  — the piece that matters for E006 — is fully covered by Actions.
