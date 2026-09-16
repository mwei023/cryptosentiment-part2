# E001 — Foundation Validation

## Receipt

```
ID:              E001
Hypothesis:      none (baseline establishment)
Foundation:      F001 (frozen)
Git commit:      6988fb5
Python:          3.13.9
Started:         2026-09-16T09:48:25Z
Completed:       2026-09-16T09:50:06Z (101s)
Capital:         $10,000
Costs:           0.1% fee + 0.05% slippage per side (0.30% round trip)
Data:            CoinGecko daily closes (365d) for V1/benchmarks;
                 Binance daily OHLC (1000 bars) for F001
Look-ahead:      NONE (bands anchored on yesterday's close; indicators
                 trailing-only; open positions force-closed at last bar)
Machine receipt: summary.json (same directory)
```

## 1. Backward validation — all strategies, identical conditions

Return over the last ~365 days of daily closes, after costs:

| Strategy | BTC ret | BTC PF | ETH ret | ETH PF | SOL ret | SOL PF |
|---|---|---|---|---|---|---|
| buy_hold | −35.25% | — | −46.85% | — | −59.11% | — |
| sma_trend (20/50) | −7.91% | 0.73 | −8.21% | 1.01 | −43.44% | 0.06 |
| band_revert (V1, S001) | −36.36% | 0.39 | −38.22% | 0.51 | −56.92% | 0.29 |
| **foundation (F001)** | **−1.06%** | 0.91 | **+1.28%** | 2.18 | **−4.70%** | 0.25 |

Foundation detail (Binance daily, 800 tradeable bars each):

| Coin | Trades | Win% | Exp/trade | Avg win | Avg loss | Max DD | Flat |
|---|---|---|---|---|---|---|---|
| BTC | 17 | 52.9% | −0.19% | +3.41% | −4.24% | 4.03% | 87.4% |
| ETH | 8 | 75.0% | +2.20% | — | — | 2.24% | — |
| SOL | 10 | 40.0% | −5.28% | — | — | 5.57% | — |

**Read:** This was a brutal window for long-only crypto (buy_hold −35% to
−59%). Against that baseline:

- V1 band mean-reversion *amplified* the drawdown it traded in
  (−36% to −57%): it kept catching knives in downtrends. D001 already
  rejected it; E001 re-confirms with identical costs on fresh data.
- F001 did its declared job — capital protection. Max drawdown 2.2–5.6%
  vs 53–75% for buy_hold, and it ended the year between −4.7% and +1.3%
  while the market lost 35–59%.
- F001 is NOT profitable in aggregate: pooled expectancy ≈ −1.1%/trade.
  ETH carried the book; SOL lost. The regime gates protected capital
  but did not find edge.

## 2. Forward validation — the /predict forecaster (bitcoin, 12 expanding folds)

| Model | MAE | Directional acc | Interval coverage (nominal 80%) |
|---|---|---|---|
| Prophet | $5,536 | 50% | 67% |
| naive (=today) | **$1,039** | — (no-change) | — |

Prophet loses to "tomorrow = today" by 5.3×, gets direction right half
the time, and its bands are overconfident. **D003 confirms the shipped
naive default.** Note this run used the *fixed* Prophet config from the
earlier session — the pre-fix configuration would have scored far worse.

## 3. Forward test / paper trade — the journal (live referee)

Journal state after E001 (backend/paper_journal.csv):

| Date | Coin | Signal | Price | Band | News sentiment | Confidence |
|---|---|---|---|---|---|---|
| 2026-09-15 | BTC | HOLD | $76,270 | inside | 19+/13−/68= | 64.71 |
| 2026-09-15 | ETH | HOLD | $2,413.88 | inside | 19+/20−/61= | 58.37 |
| 2026-09-15 | SOL | HOLD | $98.90 | inside | 25+/12−/63= | 59.94 |
| 2026-09-16 | BTC | HOLD | $75,841 | inside | 19+/11−/70= | 65.76 |
| 2026-09-16 | ETH | HOLD | $2,400.84 | inside | — | 57.99 |
| 2026-09-16 | SOL | — | — | — | — | **FAILED (429)** |

All live signals are HOLD/inside-band — consistent with the backtests:
the band system (V1) and the foundation agree there is currently no
entry. 0 settled trades yet; the win/loss table needs ~30 settled rows
before it means anything. **Operational failure recorded:** the SOL
entry died to CoinGecko rate-limiting (429 after 3 retries) — in one
process, E001's own calls plus three journal entries exhausted the free
tier. Forward runs must space out or cache. The 2026-09-15 rows prove
the journal already accumulated a day of data before E001 ran.

## What we KNOW

- Under identical costs and history, V1 band mean-reversion has
  negative cost-adjusted expectancy on BTC, ETH, and SOL (D001).
- F001's regime gates + ATR risk model cap drawdowns at 2.2–5.6% in a
  year where buy_hold drew down 53–75% on the same assets.
- F001 does not currently produce positive pooled expectancy.
- For the 1-day horizon, the naive forecaster beats Prophet by 5.3×
  MAE, and Prophet's direction accuracy is a coin flip.
- The journal mechanism works: dated, un-rewritable signal records
  with sentiment snapshots accumulate daily.

## What we SUSPECT

- F001's SOL losses are a regime-classification failure (the ADX/DI
  gates ran on 4-day candles scaled by √t on CoinGecko; the Binance
  validation path uses true daily candles and still lost), not bad
  luck. Testing this needs per-regime attribution (MARK's step 6).
- Requiring reversal confirmation before band entries (H001) would
  have removed a large share of V1's losses — V1's own trade ledger
  (13 trades/coin, all three coins negative) is the counterfactual
  dataset to test that against in E002.

## What we DON'T KNOW

- Whether ANY entry rule in this codebase has positive edge. Not one
  tested strategy beat cash after costs over this window.
- Whether sentiment (FinBERT) improves anything — deliberately untested
  until a price-only edge exists.
- Whether F001's behavior holds outside this 2.7-year mostly-bear
  window (only ~800 bars/coin tested; no 2020–21 bull included).
- Whether the stop model survives intraday gap-throughs (stops are
  evaluated on daily closes only — a stated simplification that
  flatters results).
- Whether 30 settled journal rows will confirm or contradict the
  backtests. The referee hasn't refereed anything yet.

## Known limitations

- V1/benchmarks ran on CoinGecko closes; F001 on Binance OHLC. Venues
  track closely but are not the same tape — cross-strategy return
  comparisons carry venue noise (PF/expectancy comparisons do not:
  each strategy is internally consistent).
- One window, three coins, long-only. Nothing here generalizes yet.
- CoinGecko free tier is a real operational constraint (SOL 429).

## Next

- **E002** — H001 Band Reclaim: lower band touched → close back inside
  → previous candle high broken → foundation gates. Identical data,
  costs, foundation. Compare V1 vs V2 head-to-head. Record every
  REJECTED candidate signal with its veto reason.
- Wire `journal.log_today` into Celery beat (00:05 UTC) so the referee
  accumulates rows without manual discipline.

---

## ADDENDUM (2026-09-16, after E002)

**Data-window correction.** E001's foundation arms ran on Binance
`limit=1000` daily klines — approximately **2.7 years** (2024-01 →
2026-09), not the 365 days stated above. The CoinGecko arms (V1,
benchmarks) did use 365 days. Consequences:

- Foundation vs buy_hold/sma/band comparisons above mix two windows and
  overstate the foundation's relative protection; treat cross-family
  return comparisons as indicative only. PF/expectancy comparisons
  within each family remain internally valid.
- E002 re-ran BOTH arms on the identical 1000-bar Binance tape,
  superseding the cross-venue caveat for head-to-head purposes. E001's
  headline numbers stand as first-recorded; E002 is the clean
  same-tape comparison.
- E002 also surfaced a long BTC bull segment (+30.6% buy_hold) inside
  the 1000-bar window that the 365d CoinGecko view emphasized away;
  regime-blinded conclusions drawn only from E001's table should be
  re-read with that in mind.
