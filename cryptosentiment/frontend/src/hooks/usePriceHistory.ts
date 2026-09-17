import { useEffect, useState } from "react";
import { apiErrorMessage, getPriceHistory } from "../services/api";
import type { PriceHistoryResponse } from "../types";

/**
 * usePriceHistory — fetches daily closes for the chart.
 *
 * On transient CoinGecko failures (502/429) it retries with exponential
 * backoff — the backend's market_data._get already retries internally,
 * so this mostly guards against free-tier bursts between panels.
 */
export function usePriceHistory(coin: string, days = 90) {
  const [data, setData] = useState<PriceHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const run = async (attempt: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await getPriceHistory(coin, days);
        if (!cancelled) setData(res);
      } catch (err) {
        if (cancelled) return;
        // Retry transient upstream failures up to 3 attempts total.
        if (attempt < 3 && /50[024]|429|network/i.test(apiErrorMessage(err))) {
          setTimeout(() => {
            if (!cancelled) run(attempt + 1);
          }, 1200 * 2 ** (attempt - 1));
          return;
        }
        setError(apiErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run(1);
    return () => {
      cancelled = true;
    };
  }, [coin, days]);

  return { data, loading, error };
}
