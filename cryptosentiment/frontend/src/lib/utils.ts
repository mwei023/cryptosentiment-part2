import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ForecastDay, NewsItem, SentimentLabel } from "../types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/* --------------------------------- formatters -------------------------------- */

export function formatUsd(value: number | null | undefined, maxFrac?: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  const abs = Math.abs(value);
  const frac = maxFrac ?? (abs >= 1000 ? 0 : abs >= 1 ? 2 : 4);
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: frac >= 0 ? frac : 0,
    maximumFractionDigits: Math.max(frac, 0),
  });
}

export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function formatNum(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Parse "64.71%" | 64.71 | null → number|null (confidence arrives in both forms). */
export function parseConfidence(raw: string | number | null | undefined): number | null {
  if (raw === null || raw === undefined) return null;
  const n = typeof raw === "number" ? raw : parseFloat(String(raw).replace("%", ""));
  return Number.isNaN(n) ? null : n;
}

/** Profit factor can be Infinity (no losses) — render honestly. */
export function formatProfitFactor(pf: number | undefined): string {
  if (pf === undefined || pf === null) return "--";
  if (!Number.isFinite(pf)) return "∞";
  return pf.toFixed(2);
}

/* ------------------------------- sentiment misc ------------------------------ */

export const SENTIMENT_META: Record<
  SentimentLabel,
  { text: string; chip: string; dot: string }
> = {
  POSITIVE: {
    text: "text-pos",
    chip: "border-pos/30 bg-pos/10 text-pos",
    dot: "bg-pos",
  },
  NEGATIVE: {
    text: "text-neg",
    chip: "border-neg/30 bg-neg/10 text-neg",
    dot: "bg-neg",
  },
  NEUTRAL: {
    text: "text-ink-muted",
    chip: "border-surface-line bg-surface-overlay text-ink-muted",
    dot: "bg-ink-dim",
  },
};

export function tallySentiment(news: NewsItem[]) {
  const pos = news.filter((n) => n.label === "POSITIVE").length;
  const neg = news.filter((n) => n.label === "NEGATIVE").length;
  const neu = news.filter((n) => n.label === "NEUTRAL").length;
  return { pos, neg, neu, total: news.length };
}

/* ------------------------------ signal helpers ------------------------------- */

export type Signal = "BUY" | "SELL" | "HOLD" | null;

export const SIGNAL_CHIP: Record<"BUY" | "SELL" | "HOLD", string> = {
  BUY: "border-pos/40 bg-pos/15 text-pos",
  SELL: "border-neg/40 bg-neg/15 text-neg",
  HOLD: "border-surface-line bg-surface-overlay text-ink-muted",
};

/** Band position → human label + tone. */
export function bandPositionMeta(pos: string | null | undefined): {
  label: string;
  chip: string;
} {
  switch (pos) {
    case "below_lower":
      return { label: "Below Lower Band", chip: "border-pos/40 bg-pos/10 text-pos" };
    case "above_upper":
      return { label: "Above Upper Band", chip: "border-neg/40 bg-neg/10 text-neg" };
    case "inside":
    default:
      return { label: "Inside Bands", chip: "border-surface-line bg-surface-overlay text-ink-muted" };
  }
}

/** Confidence 0-100 → color class. */
export function confidenceTone(value: number | null): string {
  if (value === null) return "text-ink-dim";
  if (value >= 70) return "text-pos";
  if (value >= 50) return "text-warn";
  return "text-neg";
}

export function confidenceBarTone(value: number | null): string {
  if (value === null) return "bg-ink-dim";
  if (value >= 70) return "bg-pos";
  if (value >= 50) return "bg-warn";
  return "bg-neg";
}

/** Latest forecast row vs today's live price → expected move. */
export function expectedMovePct(
  forecast: ForecastDay[] | null | undefined,
  livePrice: number | null | undefined
): number | null {
  if (!forecast?.length || !livePrice) return null;
  const target = forecast[forecast.length - 1].predicted;
  if (!target || !Number.isFinite(target)) return null;
  return ((target - livePrice) / livePrice) * 100;
}
