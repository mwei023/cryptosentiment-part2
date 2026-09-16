# Research Decision Log — CryptoSentiment

Append-only. Decisions cite evidence by experiment ID. Never rewrite
history: supersede with a new entry.

---

## D001 — V1 Band Mean-Reversion: REJECTED as live strategy

- **Date:** 2026-09-15 (evidence re-confirmed 2026-09-16 in E001)
- **Decision:** The original band mean-reversion strategy (S001,
  `papertrade.band_revert`) is not eligible for live capital. It is
  preserved as the permanent control (V1).
- **Evidence (E001, 365d, 0.1% fee + 0.05% slippage per side):**
  - BTC: 13 trades, PF 0.39, expectancy −2.95%/trade, return −36.4%
  - ETH: 13 trades, PF 0.51, expectancy −2.96%/trade, return −38.2%
  - SOL: 13 trades, PF 0.29, expectancy −5.44%/trade, return −56.9%
  - Win rates of 38–62% masked negative expectancy: the classic
    small-wins / big-losses profile. SMA benchmark outperformed it on
    BTC and ETH while doing nothing.
- **Reason:** Insufficient evidence of positive cost-adjusted
  expectancy on any tested asset.
- **Status:** REJECTED AS LIVE STRATEGY. Retained as historical control.

---

## D002 — Foundation F001: FROZEN FOR ENTRY RESEARCH

- **Date:** 2026-09-16
- **Decision:** The risk/regime framework (`utils/foundation.py`,
  F001: SMA200 gate, ADX/DI veto, 1% risk, 2×ATR stop, 3×ATR trail,
  4-loss kill switch) is accepted as the research foundation and
  frozen. Parameters are not to be tuned because a backtest looks bad;
  changes require a genuine bug exposed by a test.
- **Evidence (E001, Binance daily, 800 tradeable bars/coin):**
  - BTC: PF 0.91, expectancy −0.19%, return −1.06%, max DD 4.03%
  - ETH: PF 2.18, expectancy +2.20%, return +1.28%, max DD 2.24%
  - SOL: PF 0.25, expectancy −5.28%, return −4.70%, max DD 5.57%
  - vs buy_hold on the same window: −35.3% / −46.9% / −59.1%
- **Reason:** Capital protection demonstrated under identical costs —
  drawdowns 10–15× smaller than buy_hold. Acceptance does NOT imply
  profitability: pooled expectancy across the three coins remains
  negative (≈ −1.1%/trade). SOL behavior shows the gates do not yet
  reliably avoid adverse regimes.
- **Status:** FROZEN. Entry research (H001 band reclaim) proceeds on top.

---

## D003 — Forecaster: naive default CONFIRMED, Prophet demoted

- **Date:** 2026-09-16
- **Decision:** The naive forecaster (tomorrow = today + empirical
  volatility bands) remains the only default for `/predict`. Prophet is
  an experimental research path only.
- **Evidence (E001 walk-forward, bitcoin, 12 expanding folds, 1-day
  horizon):** Prophet MAE $5,536 vs naive $1,039 (5.3× worse);
  directional accuracy 50% (coin flip); 80% interval coverage 67%
  (overconfident bands).
- **Status:** CONFIRMED. No change to shipped default.

---

## D004 — H001 Band Reclaim: REJECTED (as composed)

- **Date:** 2026-09-16
- **Decision:** H001 (lower-band reversal confirmation) is rejected in
  its composed form — a mean-reversion trigger inside the F001 gate
  architecture. It is NOT retried with loosened gates (that would be
  tuning the freeze). A standalone-H001 experiment would require a new
  decision superseding D002; not opened.
- **Evidence (E002, Binance daily, ~2.7y, 3 coins):**
  - Trigger fired 10 times in ~2,400 evaluated bars; 100% vetoed by the
    F001 gate; 0 trades executed in any arm.
  - Mechanism identified: R1 (yesterday below lower band) requires a
    capitulation day; F001's gate vetoes capitulation windows by design
    (−DI dominance, SMA200 proximity, swing-structure downtrend).
  - Counterfactual: the 10 blocked candidates averaged −0.12% fwd10
    (median −1.11%, 3/10 up) — the gate's veto was directionally right.
  - Control re-confirmed: V1 pooled PF 0.68, exp −1.10%/trade (35 trades).
- **Status:** REJECTED AS COMPOSED. H002 (trend pullback, trend-aligned
  entry family) is next.

---

## D005 — H002 Trend Pullback: REJECTED

- **Date:** 2026-09-16
- **Decision:** H002 (SMA20/50 pullback-reclaim entry) is rejected as a
  live strategy. Pre-registered verdict rules were declared BEFORE the
  run (pooled trades >= 10 required; ADVANCED requires positive pooled
  expectancy AND beating the control) and were applied as written.
- **Evidence (E003, Binance daily, ~2.7y, 3 coins, 13 pooled trades):**
  - Pooled: PF 0.995, expectancy −0.01%/trade — exactly breakeven after
    costs. Control (V1): PF 0.68, exp −1.10%.
  - Per coin: BTC +1.07%, ETH +1.85%, SOL −1.67% per trade. SOL loses
    under every entry family tested (D001, D004, D005).
  - Gate compatibility measured: trend-aligned triggers pass the F001
    gate 33% of the time vs 0% for mean-reversion (E002) — the entry
    family direction is right, the edge is absent.
  - Counterfactual: 27 blocked candidates averaged +1.55% fwd10
    (median −0.31%) — the gate's net veto value is now AMBIGUOUS,
    unlike E002 where it blocked losers.
- **Status:** REJECTED. Next is E004 regime attribution of existing
  ledgers (no new hypothesis). Pre-registered: if attribution confirms
  chop-driven losses, the next change is a D-level regime/volatility
  filter decision superseding part of D002 — not another entry trigger.

---

## D006 — Regime attribution: suspicion REFUTED; composition path chosen

- **Date:** 2026-09-16
- **Decision:** The D005 suspicion ("ranging chop / SOL-style regimes
  kill the book") is REFUTED by attribution. The pre-registered filter
  proposal does NOT fire. Instead, the next experiment (E005) is a
  regime-conditional composition of already-tested cells, run with
  explicit in-sample / out-of-sample discipline. No frozen parameter is
  changed by this decision.
- **Evidence (E004, 48 trades + 37 blocked candidates, ~2.7y):**
  - All 48 trades are BULL_* by gate construction — the book has never
    traded a bear regime; bear performance of the entries is untested.
  - The killer cell is BULL_TREND (pooled exp −1.16%/trade, n=31),
    driven by V1 knife-catches (−1.84% × 23). BULL_RANGE is −0.15%.
  - Positive cells exist and are family-specific: S003×BULL_TREND
    (+0.79% × 8), V1×BULL_RANGE (+0.32% × 12).
  - Blocked BEAR_RANGE candidates averaged +4.38% fwd10 (n=21): the
    gate's bear veto may over-suppress range mean-reversion
    (AMBIGUOUS — unexecuted counterfactual, small n, one window).
  - 0/48 entries occurred on HIGH_VOL days (flag verified; entries
    cluster on calm days).
- **Status:** ATTRIBUTION RECORDED. E005 (regime-conditional book:
  V1 in BULL_RANGE, S003 in BULL_TREND, flat otherwise; in-sample
  discovery, untouched out-of-sample test) is authorized. If E005's
  out-of-sample collapse mirrors its in-sample promise, the honest
  conclusion is that no edge exists in this architecture, and the
  project record will say so.

---

## D007 — H004 Regime Book: INCONCLUSIVE (OOS silence); backtest campaign concluded

- **Date:** 2026-09-16
- **Decision:** E005's pre-registered verdict rule fires as
  INCONCLUSIVE (2 OOS trades < 5). The backtest campaign E001–E005 is
  CONCLUDED on this data window. No further entry hypotheses are run
  on the current 1000-bar tape; the null result stands until new
  evidence arrives.
- **Evidence (E005, dev 2024-07→2026-01 vs OOS 2026-01→2026-09):**
  - DEV: 20 trades, PF 1.80, exp +1.41%/trade, 75% win — best
    in-sample configuration of the project (leak-biased, n=20).
  - OOS: 2 trades, exp −5.09%; ZERO BULL_RANGE candidates in 8 months
    across all 3 coins — the book's dominant cell ceased to exist.
  - The dispatch skipped every OOS loser its components took alone
    (V1-alone +2.01% BTC was a trend-knife-catch the book refuses;
    SOL V1-alone −6.91% skipped).
- **Interpretation:** regime non-stationarity — the profitable cells
  are rare and market-year-dependent. Composition logic verified; edge
  unproven. Per D006's pre-commitment, the honest conclusion is
  recorded: no edge in this architecture has survived testing.
- **Status:** CAMPAIGN CONCLUDED. The forward paper journal
  (paper_journal.csv) is the only active instrument. Next experiment
  (E006, when ~30 settled rows exist): journal-vs-record comparison.

---

## D008 — H005 Information test: AUTHORIZED as forward dual-arm experiment

- **Date:** 2026-09-16
- **Decision:** FinBERT/news stops being decoration (a confidence
  number that never touches a decision) and becomes experiment H005:
  does the information-enhanced arm beat the price-only arm forward?
  Both arms log side by side from identical inputs; the info arm
  applies the pre-registered majority veto only
  (`papertrade.gate_with_sentiment`: BUY vetoed when neg > pos, SELL
  vetoed when pos > neg; HOLDs never become trades on news alone).
  No frozen parameter is changed by this decision. Historical
  backtesting of sentiment stays REFUSED (no NewsAPI deep history;
  survivorship-biased archives would fake it).
- **Verdict (pre-registered in E006):** 30+ settled signals per arm
  required. ADVANCED requires info expectancy AND profit factor above
  price AND vetoed-price expectancy ≤ 0 (vetoes blocked losers, not
  winners). Otherwise REJECTED. Calibration is reported, never
  verdict-driving.
- **Status:** AUTHORIZED. Journal schema upgraded V1→V2 (both arms,
  shared settlement); E006 runner reports RUNNING until maturity.
