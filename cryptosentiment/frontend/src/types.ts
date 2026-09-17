/**
 * Backend contract types — mirror the FastAPI response shapes exactly.
 *
 * Sources of truth (backend):
 * - main.py            → route handlers
 * - prediction_utils.py→ run_prediction_pipeline() result dict
 * - journal.py         → summary() (scoreboard)
 * - daily_report.py    → build_report() (daily report)
 * - papertrade.py      → daily_signal_dual()
 */

/* ---------------------------------- /predict ---------------------------------- */

export type Forecaster = "naive" | "prophet";

export interface ForecastDay {
  date: string; // "YYYY-MM-DD"
  predicted: number;
  lower: number;
  upper: number;
}

export interface PredictResponse {
  prediction: ForecastDay[];
  /** Heuristic confidence in [0, 100]; 0.0 when news unavailable. */
  confidence: number;
  db_id: number | null;
  forecaster: Forecaster;
  history_rows: number;
  news_articles: number;
  /** Present when days > 1 (experimental horizon flag). */
  warning?: string;
}

/* --------------------------------- /confidence --------------------------------- */

export interface ConfidenceResponse {
  /** String form, e.g. "64.71%". */
  confidence: string;
  sentiments_analyzed: number;
  volatility_score: number;
  note: string;
}

/* ----------------------------------- /news ------------------------------------ */

export type SentimentLabel = "POSITIVE" | "NEGATIVE" | "NEUTRAL";

export interface NewsItem {
  label: SentimentLabel;
  score: number;
  text: string;
}

/* ---------------------------------- /history ---------------------------------- */

export interface HistoryEntry {
  date: string;
  predicted: number | null;
  lower: number | null;
  upper: number | null;
  confidence: number | null;
}

export interface HistoryResponse {
  predictions: HistoryEntry[];
}

/* ------------------------------- /research/scoreboard ------------------------- */

export interface ArmStats {
  settled: number;
  wins?: number;
  losses?: number;
  win_rate_pct?: number;
  expectancy_pct?: number;
  total_net_pct?: number;
  profit_factor?: number;
}

export interface ScoreboardResponse {
  settled_rows?: number;
  vetoes?: number;
  price?: ArmStats;
  info?: ArmStats;
  /** When nothing has settled yet. */
  settled?: number;
  note?: string;
}

/* ------------------------------ /research/daily-report ------------------------ */

export interface CoinReport {
  error?: string;
  signal_price?: string;
  signal_info?: string;
  vetoed?: boolean;
  conf_price?: number;
  conf_info?: number;
  band_position?: string;
  sentiment?: { n: number | null; pos: number | null; neg: number | null; neu: number | null };
  watch?: string;
  skipped?: string;
}

export interface DailyReport {
  date: string;
  summary: ScoreboardResponse;
  deltas_vs: string | null;
  deltas: {
    price: { settled: string; expectancy: string };
    info: { settled: string; expectancy: string };
    vetoes: string;
  };
  per_coin: Record<string, CoinReport>;
  settling_tomorrow: Record<string, { price?: string; info?: string }>;
  maturity: {
    settled_slowest_arm: number;
    required_per_arm: number;
    to_go: number;
  };
}

/* ------------------------------- /research/journal --------------------------- */

/** One journal row (E006 ledger). net/win are null until the trade settles
 *  on the next day's close — the frontend must render that honestly. */
export interface JournalRow {
  date: string;
  coin_id: string;
  price: number | null;
  band_position: string;
  signal_price: string;
  signal_info: string;
  conf_price: number | null;
  conf_info: number | null;
  net_price: number | null;
  net_info: number | null;
  win_price: boolean | null;
  win_info: boolean | null;
}

export interface JournalResponse {
  rows: JournalRow[];
  summary: ScoreboardResponse;
}

/* --------------------------------- /prices ----------------------------------- */

export interface PriceHistoryResponse {
  coin_id: string;
  days: number;
  /** [timestamp_ms, close_usd] pairs, oldest-first. */
  prices: [number, number][];
}

/* --------------------------- Client-side derived state ------------------------ */

/** Current dual-arm state for one coin, distilled from the daily report.
 *  (The report carries signals/confidence/sentiment but NOT prices —
 *  live price + numeric bands come from the naive forecast response.) */
export interface CoinLiveState {
  signalPrice: string | null;
  signalInfo: string | null;
  vetoed: boolean;
  confPrice: number | null;
  confInfo: number | null;
  bandPosition: string | null;
  sentiment: CoinReport["sentiment"] | null;
  watch: string | null;
}

/* --------------------------------- API errors --------------------------------- */

/** FastAPI HTTPException body: { detail: string }. */
export interface ApiErrorBody {
  detail?: string;
}
