import React from "react";
import { cn, formatPct, formatProfitFactor } from "../../lib/utils";
import type { ArmStats } from "../../types";
import Metric from "../ui/Metric";
import Chip from "../ui/Chip";

/** ArmCard — one arm (price-only or info-enhanced) of the E006 test. */
const ArmCard: React.FC<{
  name: string;
  tag: string;
  tagTone?: "accent" | "default";
  stats: ArmStats | undefined;
  deltaSettled?: string;
  deltaExpectancy?: string;
  accent?: boolean;
}> = ({ name, tag, tagTone = "default", stats, deltaSettled, deltaExpectancy, accent }) => {
  const exp = stats?.expectancy_pct;
  return (
    <div
      className={cn(
        "rounded-xl border bg-surface-raised p-4",
        accent ? "border-accent/30" : "border-surface-line"
      )}
    >
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-[13px] font-semibold text-ink-primary">{name}</h3>
        <Chip
          className={
            tagTone === "accent"
              ? "border-accent/30 bg-accent/10 text-accent"
              : ""
          }
        >
          {tag}
        </Chip>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Metric
          label="Settled"
          value={stats?.settled ?? 0}
          caption={deltaSettled && deltaSettled !== "--" ? `Δ ${deltaSettled}` : undefined}
        />
        <Metric
          label="Expectancy"
          value={
            <span className={exp === undefined ? "" : exp >= 0 ? "text-pos" : "text-neg"}>
              {exp === undefined ? "--" : formatPct(exp, 3)}
            </span>
          }
          caption={
            deltaExpectancy && deltaExpectancy !== "--"
              ? `Δ ${deltaExpectancy}`
              : "net of 0.3% costs"
          }
        />
        <Metric
          label="Win rate"
          value={
            stats?.win_rate_pct === undefined
              ? "--"
              : `${stats.win_rate_pct.toFixed(1)}%`
          }
          caption={
            stats?.wins !== undefined
              ? `${stats.wins}W / ${stats.losses ?? 0}L`
              : undefined
          }
        />
        <Metric label="Profit factor" value={formatProfitFactor(stats?.profit_factor)} />
      </div>
    </div>
  );
};

export default ArmCard;
