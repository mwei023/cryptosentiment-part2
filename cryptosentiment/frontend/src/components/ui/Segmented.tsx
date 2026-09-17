import React from "react";
import { cn } from "../../lib/utils";

/** Segmented — radio-style button group (used for forecaster + horizon). */
const Segmented: React.FC<{
  options: { value: string; label: string; hint?: string }[];
  value: string;
  onChange: (value: string) => void;
  size?: "sm" | "md";
  className?: string;
}> = ({ options, value, onChange, size = "md", className }) => (
  <div
    role="tablist"
    className={cn(
      "inline-flex rounded-lg border border-surface-line bg-surface-base p-1",
      className
    )}
  >
    {options.map((opt) => {
      const active = opt.value === value;
      return (
        <button
          key={opt.value}
          role="tab"
          aria-selected={active}
          title={opt.hint}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md font-semibold transition",
            size === "md" ? "px-3.5 py-1.5 text-xs" : "px-2.5 py-1 text-[11px]",
            active
              ? "bg-accent/15 text-accent"
              : "text-ink-muted hover:bg-surface-overlay hover:text-ink-primary"
          )}
        >
          {opt.label}
        </button>
      );
    })}
  </div>
);

export default Segmented;
