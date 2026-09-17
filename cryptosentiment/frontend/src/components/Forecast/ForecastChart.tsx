import React from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatUsd } from "../../lib/utils";
import type { ForecastDay } from "../../types";

interface ChartRow {
  date: string;
  predicted: number;
  band: [number, number];
}

const ForecastChart: React.FC<{
  forecast: ForecastDay[];
  livePrice: number | null;
}> = ({ forecast, livePrice }) => {
  // One forecast row per day; ReferenceLine carries the live price anchor.
  const rows: ChartRow[] = forecast.map((d) => ({
    date: d.date,
    predicted: d.predicted,
    band: [d.lower, d.upper] as [number, number],
  }));

  const hasLive = livePrice !== null && Number.isFinite(livePrice);

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#1C2540" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
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
              if (name === "band") {
                const [lo, hi] = value as number[];
                return [`${formatUsd(lo)} – ${formatUsd(hi)}`, "80% band"];
              }
              return [formatUsd(value as number), "Predicted"];
            }}
          />
          <Area
            dataKey="band"
            stroke="none"
            fill="#38BDF8"
            fillOpacity={0.12}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#38BDF8"
            strokeWidth={2}
            dot={{ r: 3, fill: "#38BDF8", strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
          {hasLive && (
            <ReferenceLine
              y={livePrice as number}
              stroke="#8A94AC"
              strokeDasharray="4 4"
              label={{
                value: "now",
                position: "insideTopLeft",
                fill: "#8A94AC",
                fontSize: 10,
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ForecastChart;
