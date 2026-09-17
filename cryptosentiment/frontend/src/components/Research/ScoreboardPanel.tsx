import React from "react";
import type { ScoreboardResponse } from "../../types";
import Panel from "../ui/Panel";
import ArmCard from "./ArmCard";

/** ScoreboardPanel — E006 head-to-head: price-only vs info-enhanced arm. */
const ScoreboardPanel: React.FC<{
  scoreboard: ScoreboardResponse | null;
  report: {
    deltas: {
      price: { settled: string; expectancy: string };
      info: { settled: string; expectancy: string };
      vetoes: string;
    };
  } | null;
}> = ({ scoreboard, report }) => {
  const empty = !scoreboard || (scoreboard.settled_rows ?? 0) === 0;

  const maturity = { required_per_arm: 30, settled_slowest_arm: 0, to_go: 30 };
  let progressPct = 0;
  if (!empty) {
    // The binding constraint is the slower arm (daily_report.py logic).
    const slowest = Math.min(
      scoreboard?.price?.settled ?? 0,
      scoreboard?.info?.settled ?? 0
    );
    maturity.settled_slowest_arm = slowest;
    maturity.to_go = Math.max(0, 30 - slowest);
    progressPct = Math.min(100, (slowest / 30) * 100);
  }

  return (
    <Panel
      title="E006 · Dual-Arm Live Scoreboard"
      subtitle="H005 information test: does a FinBERT majority veto improve expectancy over price-only band signals?"
      headerRight={
        !empty && (
          <span className="num chip border-accent/30 bg-accent/10 text-accent">
            {maturity.settled_slowest_arm}/30 per arm
          </span>
        )
      }
    >
      {empty ? (
        <p className="text-[13px] text-ink-dim">
          {scoreboard?.note ??
            "No settled signals yet — arms log daily and settle on the next close. The verdict needs 30 settled trades per arm."}
        </p>
      ) : (
        <div className="space-y-5">
          {/* Maturity progress */}
          <div>
            <div className="mb-1.5 flex items-center justify-between text-[11px] text-ink-dim">
              <span>
                Maturity toward 30 settled trades per arm ·{" "}
                <span className="num">~{maturity.to_go}</span> trading days to go
              </span>
              <span className="num">{progressPct.toFixed(0)}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-surface-base">
              <div
                className="h-full rounded-full bg-accent transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* Arms */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ArmCard
              name="Arm A · Price-only"
              tag="Baseline"
              stats={scoreboard?.price}
              deltaSettled={report?.deltas?.price?.settled}
              deltaExpectancy={report?.deltas?.price?.expectancy}
            />
            <ArmCard
              name="Arm B · Info-enhanced"
              tag="FinBERT veto"
              tagTone="accent"
              accent
              stats={scoreboard?.info}
              deltaSettled={report?.deltas?.info?.settled}
              deltaExpectancy={report?.deltas?.info?.expectancy}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-surface-line pt-3 text-[11px] text-ink-dim">
            <span>
              Settled rows <span className="num text-ink-primary">{scoreboard?.settled_rows ?? 0}</span>
              {" · "}
              Sentiment vetoes <span className="num text-ink-primary">{scoreboard?.vetoes ?? 0}</span>
              {report?.deltas?.vetoes && report.deltas.vetoes !== "--" && (
                <span className="num"> (Δ {report.deltas.vetoes})</span>
              )}
            </span>
            <span>Settlement scores each non-HOLD arm against the next day's close, net of 0.3% round-trip costs.</span>
          </div>
        </div>
      )}
    </Panel>
  );
};

export default ScoreboardPanel;
