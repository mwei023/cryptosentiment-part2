import React from "react";
import { cn, formatUsd } from "../../lib/utils";
import type { ForecastDay } from "../../types";

/**
 * BandPositionCard — shows where the live price sits relative to the
 * 80% volatility bands that would trigger tomorrow's BUY/SELL signals.
 * Numeric bands come from the latest naive forecast (the same bands the
 * backend journal uses; the report itself only carries a text watch line).
 */
const BandPositionCard: React.FC<{
  forecast: ForecastDay[] | null;
  livePrice: number | null;
  bandPosition: string | null;
}> = ({ forecast, livePrice, bandPosition }) => {
  if (!forecast?.length || livePrice === null) {
    return (
      <p className="text-[13px] text-ink-dim">
        Run a forecast to see band positioning.
      </p>
    );
  }

  const lower = forecast[forecast.length - 1].lower;
  const upper = forecast[forecast.length - 1].upper;
  const span = upper - lower;
  const clamped = Math.min(Math.max(livePrice, lower - span * 0.1), upper + span * 0.1);
  const posPct = span > 0 ? ((clamped - (lower - span * 0.1)) / (span * 1.2)) * 100 : 50;

  const inside = livePrice >= lower && livePrice <= upper;
  const below = livePrice < lower;
  const above = livePrice > upper;

  const markerTone = below
    ? "bg-pos"
    : above
    ? "bg-neg"
    : "bg-accent";

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between text-xs">
        <div>
          <p className="text-ink-dim">Lower (BUY trigger)</p>
          <p className="num font-semibold text-pos">{formatUsd(lower)}</p>
        </div>
        <div className="text-center">
          <p className="text-ink-dim">Last close</p>
          <p className="num font-semibold text-ink-primary">{formatUsd(livePrice)}</p>
        </div>
        <div className="text-right">
          <p className="text-ink-dim">Upper (SELL trigger)</p>
          <p className="num font-semibold text-neg">{formatUsd(upper)}</p>
        </div>
      </div>

      {/* Band rail */}
      <div className="relative h-3 rounded-full border border-surface-line bg-surface-base">
        <div className="absolute inset-y-0 left-[8.33%] right-[8.33%] rounded-full bg-accent/15" />
        <div
          className="absolute top-1/2 h-4 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ left: `${posPct}%` }}
        >
          <div className={cn("h-full w-full rounded-full shadow", markerTone)} />
        </div>
      </div>
      <div className="flex justify-between text-[10px] uppercase tracking-wider text-ink-dim">
        <span className="text-pos">buy zone</span>
        <span>{inside ? "inside bands" : below ? "below lower band" : "above upper band"}</span>
        <span className="text-neg">sell zone</span>
      </div>

      {bandPosition && bandPosition !== "inside" && (
        <p className="text-[11px] text-warn">
          Journal position for today: {bandPosition.replace("_", " ")}
        </p>
      )}
    </div>
  );
};

export default BandPositionCard;
