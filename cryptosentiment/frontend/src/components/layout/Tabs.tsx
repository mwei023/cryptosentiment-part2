import React from "react";
import { cn } from "../../lib/utils";

export type TabId = "forecast" | "sentiment" | "research" | "history";

const TABS: { id: TabId; label: string; hint: string }[] = [
  { id: "forecast", label: "Forecast", hint: "Price prediction & confidence" },
  { id: "sentiment", label: "Sentiment", hint: "FinBERT news analysis" },
  { id: "research", label: "Research", hint: "E006 dual-arm scoreboard" },
  { id: "history", label: "History", hint: "Stored predictions from DB" },
];

const Tabs: React.FC<{
  active: TabId;
  onChange: (id: TabId) => void;
  className?: string;
}> = ({ active, onChange, className }) => (
  <nav
    className={cn("flex gap-1 overflow-x-auto border-b border-surface-line", className)}
    aria-label="Sections"
    role="tablist"
  >
    {TABS.map((t) => {
      const isActive = t.id === active;
      return (
        <button
          key={t.id}
          role="tab"
          aria-selected={isActive}
          onClick={() => onChange(t.id)}
          title={t.hint}
          className={cn(
            "relative whitespace-nowrap px-4 py-2.5 text-[13px] font-semibold transition",
            isActive
              ? "text-accent"
              : "text-ink-muted hover:text-ink-primary"
          )}
        >
          {t.label}
          {isActive && (
            <span
              aria-hidden
              className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
            />
          )}
        </button>
      );
    })}
  </nav>
);

export default Tabs;
