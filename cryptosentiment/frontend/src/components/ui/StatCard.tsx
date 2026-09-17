import React from "react";
import { cn, formatUsd } from "../../lib/utils";

/** StatCard — hero KPI tile for the top strip (price, confidence, signals). */
const StatCard: React.FC<{
  label: string;
  value: string;
  caption?: React.ReactNode;
  tone?: "default" | "pos" | "neg" | "warn" | "accent";
  className?: string;
}> = ({ label, value, caption, tone = "default", className }) => {
  const toneClass = {
    default: "text-ink-primary",
    pos: "text-pos",
    neg: "text-neg",
    warn: "text-warn",
    accent: "text-accent",
  }[tone];

  return (
    <div className={cn("panel px-5 py-4", className)}>
      <p className="text-[11px] font-medium uppercase tracking-wider text-ink-dim">
        {label}
      </p>
      <p className={cn("num mt-1.5 text-2xl font-bold leading-none", toneClass)}>
        {value}
      </p>
      {caption && (
        <p className="mt-2 truncate text-[11px] text-ink-muted">{caption}</p>
      )}
    </div>
  );
};

/** Convenience: price card that formats USD and shows band context. */
export const PriceStat: React.FC<{
  price: number | null;
  caption?: React.ReactNode;
  className?: string;
}> = ({ price, caption, className }) => (
  <StatCard
    label="Live Price"
    value={price === null ? "--" : formatUsd(price)}
    caption={caption}
    tone="accent"
    className={className}
  />
);

export default StatCard;
