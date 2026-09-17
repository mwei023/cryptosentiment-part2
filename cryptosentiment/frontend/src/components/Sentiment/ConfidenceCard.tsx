import React, { useEffect, useState } from "react";
import { apiErrorMessage, getConfidence } from "../../services/api";
import {
  confidenceBarTone,
  confidenceTone,
  parseConfidence,
} from "../../lib/utils";
import Spinner from "../ui/Spinner";

/**
 * ConfidenceCard — live /confidence/{coin} score with the three
 * weighted components explained (agreement 50 / vol 30 / sample 20).
 */
const ConfidenceCard: React.FC<{ coin: string }> = ({ coin }) => {
  const [data, setData] = useState<{
    value: number | null;
    articles: number;
    volatility: number;
    note: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getConfidence(coin)
      .then((res) => {
        if (cancelled) return;
        setData({
          value: parseConfidence(res.confidence),
          articles: res.sentiments_analyzed,
          volatility: res.volatility_score,
          note: res.note,
        });
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

  const v = data?.value ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <p className="num text-4xl font-bold leading-none">
            <span className={confidenceTone(v)}>
              {v === null ? "--" : `${v.toFixed(1)}%`}
            </span>
          </p>
          <p className="mt-1 text-[11px] text-ink-dim">
            {data?.articles ?? 0} FinBERT-scored headlines · daily vol{" "}
            <span className="num">{data ? data.volatility.toFixed(4) : "--"}</span>
          </p>
        </div>
      </div>

      <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface-base">
        <div
          className={`h-full rounded-full transition-all duration-500 ${confidenceBarTone(v)}`}
          style={{ width: `${v ?? 0}%` }}
        />
      </div>

      {/* Component weights (from confidence_calculator.py) */}
      <div className="space-y-1.5 text-[11px] text-ink-muted">
        <div className="flex justify-between">
          <span>Headline agreement</span>
          <span className="num">weight 0.50</span>
        </div>
        <div className="flex justify-between">
          <span>Volatility regime (caps at 8% daily)</span>
          <span className="num">weight 0.30</span>
        </div>
        <div className="flex justify-between">
          <span>Sample size (20 headlines = full)</span>
          <span className="num">weight 0.20</span>
        </div>
      </div>

      <p className="border-t border-surface-line pt-3 text-[11px] leading-relaxed text-ink-dim">
        {data?.note}
      </p>
    </div>
  );
};

export default ConfidenceCard;
