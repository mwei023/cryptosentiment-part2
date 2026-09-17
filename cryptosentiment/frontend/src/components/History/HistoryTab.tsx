import React, { useEffect, useState } from "react";
import { apiErrorMessage, getHistory } from "../../services/api";
import { confidenceBarTone, formatUsd } from "../../lib/utils";
import type { HistoryEntry } from "../../types";
import Panel from "../ui/Panel";
import Spinner from "../ui/Spinner";

/** HistoryTab — persisted predictions (/history/{coin}) from PostgreSQL. */
const HistoryTab: React.FC<{ coin: string }> = ({ coin }) => {
  const [rows, setRows] = useState<HistoryEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getHistory(coin)
      .then((res) => {
        if (!cancelled) setRows(res.predictions ?? []);
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

  const sorted = rows
    ? [...rows].sort((a, b) => (a.date < b.date ? 1 : -1))
    : null;

  return (
    <Panel
      title="Prediction History"
      subtitle={`Persisted forecasts for ${coin} (newest first)`}
      bodyClassName="p-0"
    >
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner className="h-5 w-5 text-ink-dim" />
        </div>
      ) : error ? (
        <p className="p-5 text-[13px] text-neg" role="alert">
          ⚠ {error}
        </p>
      ) : !sorted || sorted.length === 0 ? (
        <p className="p-5 text-[13px] text-ink-dim">
          No predictions stored yet. Run a forecast in the Forecast tab —
          each run persists to the database and appears here.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left">
            <thead className="border-b border-surface-line">
              <tr>
                <th className="th">Generated</th>
                <th className="th">Predicted</th>
                <th className="th">80% band</th>
                <th className="th">Range width</th>
                <th className="th">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-line/60">
              {sorted.map((p, i) => {
                const width =
                  p.lower != null && p.upper != null && p.predicted
                    ? ((p.upper - p.lower) / p.predicted) * 100
                    : null;
                const lowerPct =
                  p.lower != null && p.upper != null && p.upper > p.lower
                    ? ((p.predicted! - p.lower) / (p.upper - p.lower)) * 100
                    : 50;
                return (
                  <tr key={i} className="transition hover:bg-surface-raised/60">
                    <td className="td num text-ink-muted">{p.date}</td>
                    <td className="td num font-semibold text-ink-primary">
                      {formatUsd(p.predicted)}
                    </td>
                    <td className="td">
                      {/* Mini band bar: predicted marker inside lower–upper range */}
                      <div className="flex items-center gap-3">
                        <span className="num text-[11px] text-pos">
                          {formatUsd(p.lower)}
                        </span>
                        <div className="relative h-1.5 w-28 rounded-full bg-surface-base">
                          <div
                            className="absolute top-1/2 h-2.5 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent"
                            style={{ left: `${Math.min(Math.max(lowerPct, 0), 100)}%` }}
                          />
                        </div>
                        <span className="num text-[11px] text-neg">
                          {formatUsd(p.upper)}
                        </span>
                      </div>
                    </td>
                    <td className="td num text-ink-muted">
                      {width === null ? "--" : `±${(width / 2).toFixed(1)}%`}
                    </td>
                    <td className="td">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-base">
                          <div
                            className={`h-full ${confidenceBarTone(p.confidence)}`}
                            style={{ width: `${Math.min(Math.max(p.confidence ?? 0, 0), 100)}%` }}
                          />
                        </div>
                        <span className="num text-[12px] text-ink-muted">
                          {p.confidence != null ? `${p.confidence.toFixed(1)}%` : "--"}
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
};

export default HistoryTab;
