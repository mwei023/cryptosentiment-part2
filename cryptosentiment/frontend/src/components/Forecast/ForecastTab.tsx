import React from "react";
import { useEffect, useState } from "react";
import {
  apiErrorMessage,
  predict,
} from "../../services/api";
import {
  confidenceTone,
  expectedMovePct,
  formatPct,
  formatUsd,
} from "../../lib/utils";
import type {
  CoinLiveState,
  Forecaster,
  PredictResponse,
} from "../../types";
import Panel from "../ui/Panel";
import Metric from "../ui/Metric";
import StatCard, { PriceStat } from "../ui/StatCard";
import ForecastControls from "./ForecastControls";
import ForecastChart from "./ForecastChart";
import BandPositionCard from "./BandPositionCard";
import PriceHistoryCard from "./PriceHistoryCard";

const ForecastTab: React.FC<{
  coin: string;
  live: CoinLiveState | null;
}> = ({ coin, live }) => {
  const [forecaster, setForecaster] = useState<Forecaster>("naive");
  const [days, setDays] = useState(1);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await predict(coin, days, forecaster);
      setResult(res);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  // Re-run automatically when the coin changes (fresh forecast per asset).
  useEffect(() => {
    setResult(null);
    setError(null);
  }, [coin]);

  const forecast = result?.prediction ?? null;
  // Live price: the forecast's first row IS today's close for the naive
  // forecaster (predicted = last close), so anchor everything to it.
  const livePrice = forecast?.length ? forecast[0].predicted : null;
  const move = expectedMovePct(forecast, livePrice);
  const conf = result?.confidence ?? null;

  return (
    <div className="space-y-5">
      {/* Stat strip */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <PriceStat
          price={livePrice}
          caption={forecast ? `${result?.history_rows ?? 0} history rows` : "Run a forecast"}
        />
        <StatCard
          label="Confidence"
          value={conf === null ? "--" : `${conf.toFixed(1)}%`}
          tone={
            conf === null ? "default" : conf >= 70 ? "pos" : conf >= 50 ? "warn" : "neg"
          }
          caption="Heuristic — not a calibrated probability"
        />
        <StatCard
          label={`Expected move (${days}d)`}
          value={move === null ? "--" : formatPct(move)}
          tone={move === null ? "default" : move >= 0 ? "pos" : "neg"}
          caption={forecast ? `to ${formatUsd(forecast[forecast.length - 1].predicted)}` : "—"}
        />
        <StatCard
          label="News articles"
          value={result ? String(result.news_articles) : "--"}
          caption={live?.sentiment?.n != null ? `${live.sentiment.n} in latest journal row` : undefined}
        />
      </div>

      {/* Market context: 90d closes + forecast overlay */}
      <PriceHistoryCard coin={coin} forecast={forecast} />

      <Panel title="Forecast Engine" bodyClassName="p-5 space-y-5">
        <ForecastControls
          forecaster={forecaster}
          onForecasterChange={setForecaster}
          days={days}
          onDaysChange={setDays}
          onRun={run}
          loading={loading}
          error={error}
          hasResult={!!result}
        />

        {forecast && forecast.length > 0 && (
          <>
            <div className="border-t border-surface-line pt-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-[13px] font-semibold text-ink-primary">
                  Predicted path · 80% band
                </h3>
                {result?.warning && (
                  <span className="chip border-warn/30 bg-warn/10 text-warn" title={result.warning}>
                    experimental horizon
                  </span>
                )}
              </div>
              <ForecastChart forecast={forecast} livePrice={livePrice} />
            </div>

            <div className="grid grid-cols-1 gap-5 border-t border-surface-line pt-4 lg:grid-cols-2">
              <div>
                <h3 className="mb-3 text-[13px] font-semibold text-ink-primary">
                  Band position vs tomorrow's triggers
                </h3>
                <BandPositionCard
                  forecast={forecast}
                  livePrice={livePrice}
                  bandPosition={live?.bandPosition ?? null}
                />
              </div>
              <div>
                <h3 className="mb-3 text-[13px] font-semibold text-ink-primary">
                  Forecast detail
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {forecast.map((d) => (
                    <Metric
                      key={d.date}
                      label={d.date}
                      value={formatUsd(d.predicted)}
                      caption={`${formatUsd(d.lower)} – ${formatUsd(d.upper)}`}
                    />
                  ))}
                </div>
                <p className="mt-4 text-[11px] leading-relaxed text-ink-dim">
                  Confidence blends FinBERT headline agreement (50%), the
                  volatility regime (30%), and sample size (20%). It is a
                  heuristic score, not a calibrated probability.
                </p>
                <p className="mt-1 text-[11px] text-ink-dim">
                  Confidence tone:{" "}
                  <span className={confidenceTone(conf)}>
                    {conf === null ? "unknown" : conf >= 70 ? "high" : conf >= 50 ? "moderate" : "low"}
                  </span>
                </p>
              </div>
            </div>
          </>
        )}

        {!forecast && !loading && !error && (
          <p className="border-t border-surface-line pt-4 text-[13px] text-ink-dim">
            Select a forecaster and press{" "}
            <span className="font-semibold text-ink-primary">Run forecast</span>{" "}
            — the pipeline fetches 365 days of history, fits bands, scores
            FinBERT headlines, and persists the result.
          </p>
        )}
      </Panel>
    </div>
  );
};

export default ForecastTab;
