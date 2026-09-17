import React from "react";
import type { Forecaster } from "../../types";
import Segmented from "../ui/Segmented";
import Spinner from "../ui/Spinner";

export const HORIZON_OPTIONS = [
  { value: "1", label: "1 day", hint: "Walk-forward validated horizon" },
  { value: "3", label: "3 days", hint: "√t diffusion bands (experimental)" },
  { value: "7", label: "7 days", hint: "Maximum horizon (experimental)" },
];

const ForecastControls: React.FC<{
  forecaster: Forecaster;
  onForecasterChange: (f: Forecaster) => void;
  days: number;
  onDaysChange: (d: number) => void;
  onRun: () => void;
  loading: boolean;
  error: string | null;
  hasResult: boolean;
}> = ({
  forecaster,
  onForecasterChange,
  days,
  onDaysChange,
  onRun,
  loading,
  error,
  hasResult,
}) => (
  <div className="space-y-3">
    <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div>
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-dim">
          Forecaster
        </p>
        <Segmented
          value={forecaster}
          onChange={(v) => onForecasterChange(v as Forecaster)}
          options={[
            {
              value: "naive",
              label: "Naive + Vol Bands",
              hint: "Validated: tomorrow = today ± 80% empirical bands (beats Prophet 3–6× MAE)",
            },
            {
              value: "prophet",
              label: "Prophet",
              hint: "Experimental research path — loses to naive at 1-day horizon",
            },
          ]}
        />
      </div>

      <div>
        <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-dim">
          Horizon
        </p>
        <Segmented
          value={String(days)}
          onChange={(v) => onDaysChange(Number(v))}
          options={HORIZON_OPTIONS}
          size="sm"
        />
      </div>

      <button onClick={onRun} disabled={loading} className="btn btn-primary ml-auto">
        {loading ? <Spinner /> : "▶"}
        {loading ? "Running pipeline…" : hasResult ? "Re-run forecast" : "Run forecast"}
      </button>
    </div>

    <p className="text-[11px] leading-relaxed text-ink-dim">
      {forecaster === "naive"
        ? "Validated default: next-day close = today's close, with an 80% band from 30-day log-return volatility. Walk-forward on BTC/ETH/SOL beats Prophet 3–6× on MAE."
        : "Experimental: Prophet with weekly seasonality only — no holidays, no yearly cycle. Walk-forward shows 50% directional accuracy; research use only."}
      {days > 1 && " Horizons beyond 1 day scale bands by √t and are not walk-forward validated."}
    </p>

    {error && (
      <div
        role="alert"
        className="rounded-lg border border-neg/30 bg-neg/10 px-3.5 py-2.5 text-[13px] text-neg"
      >
        ⚠ {error}
      </div>
    )}
  </div>
);

export default ForecastControls;
