import React from "react";
import { cn } from "../../lib/utils";

/** Metric — compact KPI display (label, mono value, optional caption). */
const Metric: React.FC<{
  label: string;
  value: React.ReactNode;
  caption?: React.ReactNode;
  className?: string;
}> = ({ label, value, caption, className }) => (
  <div className={cn("min-w-0", className)}>
    <p className="text-[11px] font-medium uppercase tracking-wider text-ink-dim">
      {label}
    </p>
    <p className="num mt-1 truncate text-xl font-bold text-ink-primary">{value}</p>
    {caption && <p className="mt-0.5 truncate text-[11px] text-ink-dim">{caption}</p>}
  </div>
);

export default Metric;
