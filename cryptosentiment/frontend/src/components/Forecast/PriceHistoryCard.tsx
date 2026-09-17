import React, { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatUsd } from "../../lib/utils";
import { usePriceHistory } from "../../hooks/usePriceHistory";
import type { ForecastDay } from "../../types";
import Panel from "../ui/Panel";
import Spinner from "../ui/Spinner";

const RANGES = [
  { days: 30, label: "1M" },
  { days: 90, label: "3M" },
  { days: 180, label: "6M" },
  { days: 365, label: "1Y" },
];

/** PriceHistoryCard — daily closes with forecast overlay + live range picker. */
const PriceHistoryCard: React.FC<{
  coin: string;
  forecast: ForecastDay[] | null;
  height?: number;
}> = ({ coin, forecast, height = 280 }) => {
  const [days, setDays] = useState(90);
  const { data, loading, error } = usePriceHistory(coin, days);

  const { history, forecastTail, lastClose, changePct } = useMemo(() => {
    const rows = (data?.prices ?? []).map(([ts, close]) => ({
      date: new Date(ts).toISOString().slice(0, 10),
      close,
    }));
    // Attach the forecast as a separate series so it visually continues
    // the history line (dashed area). Dates don't collide: forecast days
    // start after the last history day.
    const fRows = (forecast ?? []).map((f) => ({
      date: f.date,
      close: null as number | null,
      pred: f.predicted,
      band: [f.lower, f.upper] as [number, number] | undefined,
    }));
    const last = rows.length ? rows[rows.length - 1].close : null;
    const first = rows.length ? rows[0].close : null;
    const pct =
      first && last && first > 0 ? ((last - first) / first) * 100 : null;
    return {
      history: rows,
      forecastTail: fRows,
      lastClose: last,
      changePct: pct,
    };
  }, [data, forecast]);

  // Merge history + forecast rows on the shared date axis.
  const merged = useMemo(() => {
    const map = new Map<string, { date: string; close: number | null; pred?: number; band?: [number, number] }>();
    for (const r of history) map.set(r.date, { date: r.date, close: r.close });
    for (const f of forecastTail) {
      const existing = map.get(f.date);
      map.set(f.date, {
        date: f.date,
        close: existing?.close ?? null,
        pred: f.pred,
        band: f.band,
      });
    }
    return Array.from(map.values()).sort((a, b) => (a.date < b.date ? -1 : 1));
  }, [history, forecastTail]);

  return (
    <Panel
      title={`Price History · ${coin}`}
      subtitle="CoinGecko daily closes; forecast overlay shown where available"
      headerRight={
        <div className="flex items-center gap-1 rounded-lg border border-surface-line bg-surface-base p-1">
          {RANGES.map((r) => (
            <button
              key={r.days}
              onClick={() => setDays(r.days)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition ${
                days === r.days
                  ? "bg-accent/15 text-accent"
                  : "text-ink-muted hover:text-ink-primary"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      }
    >
      {loading ? (
        <div className="flex items-center justify-center" style={{ height }}>
          <Spinner className="h-5 w-5 text-ink-dim" />
        </div>
      ) : error ? (
        <p className="text-[13px] text-neg" role="alert" style={{ paddingTop: height / 2 - 20 }}>
          ⚠ {error}
        </p>
      ) : merged.length < 2 ? (
        <p className="text-[13px] text-ink-dim" style={{ paddingTop: height / 2 - 20 }}>
          Not enough price data returned for this range.
        </p>
      ) : (
        <>
          <div className="mb-3 flex items-baseline gap-3">
            <span className="num text-xl font-bold text-ink-primary">
              {formatUsd(lastClose)}
            </span>
            {changePct !== null && (
              <span
                className={`num text-[13px] font-semibold ${
                  changePct >= 0 ? "text-pos" : "text-neg"
                }`}
              >
                {changePct >= 0 ? "+" : ""}
                {changePct.toFixed(2)}% · {days}d
              </span>
            )}
          </div>

          <div style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={merged}
                margin={{ top: 6, right: 12, bottom: 0, left: 0 }}
              >
                <defs>
                  <linearGradient id="closeFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#1C2540" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  minTickGap={40}
                  tick={{ fill: "#8A94AC", fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: "#1C2540" }}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  tick={{ fill: "#8A94AC", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => formatUsd(v, 0)}
                  width={78}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0C111E",
                    border: "1px solid #1C2540",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#E9EEF8", fontWeight: 600 }}
                  formatter={(value: number | number[], name: string) => {
                    if (name === "band" && Array.isArray(value)) {
                      const [lo, hi] = value as number[];
                      return [`${formatUsd(lo)} – ${formatUsd(hi)}`, "forecast band"];
                    }
                    if (name === "pred") return [formatUsd(value as number), "Forecast"];
                    if (value === null || value === undefined) return [null, ""];
                    return [formatUsd(value as number), "Close"];
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="#38BDF8"
                  strokeWidth={1.8}
                  fill="url(#closeFill)"
                  connectNulls={false}
                  isAnimationActive={false}
                />
                {forecastTail.length > 0 && (
                  <>
                    <Area
                      type="monotone"
                      dataKey="band"
                      stroke="none"
                      fill="#FBBF24"
                      fillOpacity={0.10}
                      isAnimationActive={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="pred"
                      stroke="#FBBF24"
                      strokeDasharray="5 4"
                      strokeWidth={1.6}
                      fill="none"
                      dot={false}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  </>
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Panel>
  );
};

export default PriceHistoryCard;
