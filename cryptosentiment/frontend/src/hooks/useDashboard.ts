import { useCallback, useEffect, useRef, useState } from "react";
import {
  apiErrorMessage,
  getDailyReport,
  getJournal,
  getScoreboard,
} from "../services/api";
import type {
  CoinLiveState,
  DailyReport,
  JournalResponse,
  ScoreboardResponse,
} from "../types";

/** CoinGecko slugs tracked by the E006 journal (daily_report.py CORE_COINS). */
export const CORE_COINS = [
  { id: "bitcoin", name: "Bitcoin", symbol: "BTC" },
  { id: "ethereum", name: "Ethereum", symbol: "ETH" },
  { id: "solana", name: "Solana", symbol: "SOL" },
  { id: "binancecoin", name: "BNB", symbol: "BNB" },
  { id: "cardano", name: "Cardano", symbol: "ADA" },
  { id: "ripple", name: "XRP", symbol: "XRP" },
  { id: "dogecoin", name: "Dogecoin", symbol: "DOGE" },
] as const;

export const COIN_IDS: readonly string[] = CORE_COINS.map((c) => c.id);
export const isKnownCoin = (id: string) => COIN_IDS.includes(id);

/**
 * Distill the daily report's per_coin row into view state.
 *
 * The report does NOT carry price/bands (those live in the journal CSV);
 * live price + numeric bands come from the naive forecast instead.
 */
function extractLiveState(
  report: DailyReport | null,
  coin: string
): CoinLiveState | null {
  if (!report) return null;
  const r = report.per_coin?.[coin];
  if (!r || r.error) return null;
  return {
    signalPrice: r.signal_price ?? null,
    signalInfo: r.signal_info ?? null,
    vetoed: Boolean(r.vetoed),
    confPrice: r.conf_price ?? null,
    confInfo: r.conf_info ?? null,
    bandPosition: r.band_position ?? null,
    sentiment: r.sentiment ?? null,
    watch: r.watch ?? null,
  };
}

/**
 * Central data hook: loads research state (report + scoreboard) on coin
 * change and exposes it to every panel. Panel-specific data (forecast,
 * news, history) is fetched by their own components/handlers.
 */
export function useDashboard() {
  const [coin, setCoin] = useState("bitcoin");
  const [report, setReport] = useState<DailyReport | null>(null);
  const [scoreboard, setScoreboard] = useState<ScoreboardResponse | null>(null);
  const [journalRows, setJournalRows] = useState<JournalResponse["rows"]>([]);
  const [researchLoading, setResearchLoading] = useState(true);
  const [researchError, setResearchError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const seq = useRef(0);

  const loadResearch = useCallback(async () => {
    const mySeq = ++seq.current;
    setResearchLoading(true);
    setResearchError(null);
    try {
      const [rep, score, jrnl] = await Promise.all([
        getDailyReport(),
        getScoreboard(),
        getJournal(),
      ]);
      if (seq.current !== mySeq) return; // a newer request superseded us
      setReport(rep);
      setScoreboard(score);
      setJournalRows(jrnl.rows);
      setLastRefreshed(new Date());
    } catch (err) {
      if (seq.current !== mySeq) return;
      setResearchError(apiErrorMessage(err));
    } finally {
      if (seq.current === mySeq) setResearchLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResearch();
  }, [coin, loadResearch]);

  const live: CoinLiveState | null = extractLiveState(report, coin);

  return {
    coin,
    setCoin,
    report,
    scoreboard,
    journalRows,
    live,
    researchLoading,
    researchError,
    lastRefreshed,
    reloadResearch: loadResearch,
  };
}
