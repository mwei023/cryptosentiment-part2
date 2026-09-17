import React, { useEffect, useState } from "react";
import { apiErrorMessage, getNews } from "../../services/api";
import { SENTIMENT_META, tallySentiment } from "../../lib/utils";
import type { NewsItem } from "../../types";
import Chip from "../ui/Chip";
import Spinner from "../ui/Spinner";

/** NewsFeed — headlines with FinBERT labels, tallied pos/neu/neg. */
const NewsFeed: React.FC<{ coin: string }> = ({ coin }) => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getNews(coin)
      .then((items) => {
        if (!cancelled) setNews(items);
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [coin]);

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center text-ink-dim">
        <Spinner className="h-5 w-5" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-[13px] text-neg" role="alert">
        ⚠ {error}
      </p>
    );
  }

  if (news.length === 0) {
    return (
      <p className="text-[13px] text-ink-dim">
        No news articles found for this asset.
      </p>
    );
  }

  const { pos, neg, neu, total } = tallySentiment(news);

  return (
    <div className="space-y-4">
      {/* Tally strip */}
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <Chip className="border-pos/30 bg-pos/10 text-pos">{pos} positive</Chip>
        <Chip className="border-surface-line bg-surface-overlay text-ink-muted">
          {neu} neutral
        </Chip>
        <Chip className="border-neg/30 bg-neg/10 text-neg">{neg} negative</Chip>
        <span className="num ml-auto text-ink-dim">{total} scored</span>
      </div>

      {/* Distribution bar */}
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-base">
        {pos > 0 && (
          <div className="bg-pos" style={{ width: `${(pos / total) * 100}%` }} />
        )}
        {neu > 0 && (
          <div className="bg-ink-dim" style={{ width: `${(neu / total) * 100}%` }} />
        )}
        {neg > 0 && (
          <div className="bg-neg" style={{ width: `${(neg / total) * 100}%` }} />
        )}
      </div>

      {/* Headlines */}
      <ul className="max-h-[480px] space-y-2 overflow-y-auto pr-1">
        {news.map((item, i) => {
          const meta = SENTIMENT_META[item.label] ?? SENTIMENT_META.NEUTRAL;
          return (
            <li
              key={i}
              className="flex items-start gap-3 rounded-lg border border-surface-line bg-surface-raised px-3.5 py-2.5"
            >
              <span
                aria-hidden
                className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${meta.dot}`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] leading-snug text-ink-primary">
                  {item.text}
                </p>
                <p className="mt-1 text-[11px] text-ink-dim">
                  <span className={meta.text}>{item.label}</span>
                  <span className="num"> · {(item.score * 100).toFixed(1)}%</span>
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default NewsFeed;
