import {
  bandPositionMeta,
  confidenceTone,
  expectedMovePct,
  formatNum,
  formatPct,
  formatProfitFactor,
  formatUsd,
  parseConfidence,
  tallySentiment,
} from "./utils";
import type { ForecastDay, NewsItem } from "../types";

describe("formatters", () => {
  test("formatUsd handles null/NaN and scales decimals", () => {
    expect(formatUsd(null)).toBe("--");
    expect(formatUsd(NaN)).toBe("--");
    expect(formatUsd(76270.42)).toBe("$76,270");
    expect(formatUsd(2413.884)).toBe("$2,414"); // ≥ 1000 → whole dollars
    expect(formatUsd(413.884)).toBe("$413.88");
    expect(formatUsd(0.5432)).toBe("$0.5432");
    expect(formatUsd(100.5, 1)).toBe("$100.5");
  });

  test("formatPct signs and formats", () => {
    expect(formatPct(null)).toBe("--");
    expect(formatPct(1.234)).toBe("+1.23%");
    expect(formatPct(-1.234)).toBe("-1.23%");
    expect(formatPct(0)).toBe("0.00%");
  });

  test("formatNum", () => {
    expect(formatNum(null)).toBe("--");
    expect(formatNum(64.707, 1)).toBe("64.7");
  });

  test("formatProfitFactor handles infinity", () => {
    expect(formatProfitFactor(undefined)).toBe("--");
    expect(formatProfitFactor(Infinity)).toBe("∞");
    expect(formatProfitFactor(1.234)).toBe("1.23");
  });

  test("parseConfidence accepts both string and number forms", () => {
    expect(parseConfidence("64.71%")).toBe(64.71);
    expect(parseConfidence(58.37)).toBe(58.37);
    expect(parseConfidence(null)).toBeNull();
    expect(parseConfidence("nonsense")).toBeNull();
  });
});

describe("sentiment + signals", () => {
  const news: NewsItem[] = [
    { label: "POSITIVE", score: 0.9, text: "a" },
    { label: "POSITIVE", score: 0.8, text: "b" },
    { label: "NEGATIVE", score: 0.7, text: "c" },
    { label: "NEUTRAL", score: 0.6, text: "d" },
  ];

  test("tallySentiment counts each label", () => {
    expect(tallySentiment(news)).toEqual({ pos: 2, neg: 1, neu: 1, total: 4 });
    expect(tallySentiment([])).toEqual({ pos: 0, neg: 0, neu: 0, total: 0 });
  });

  test("bandPositionMeta maps backend positions", () => {
    expect(bandPositionMeta("below_lower").label).toBe("Below Lower Band");
    expect(bandPositionMeta("above_upper").label).toBe("Above Upper Band");
    expect(bandPositionMeta("inside").label).toBe("Inside Bands");
    expect(bandPositionMeta(null).label).toBe("Inside Bands");
  });

  test("confidenceTone buckets", () => {
    expect(confidenceTone(75)).toBe("text-pos");
    expect(confidenceTone(60)).toBe("text-warn");
    expect(confidenceTone(30)).toBe("text-neg");
    expect(confidenceTone(null)).toBe("text-ink-dim");
  });
});

describe("expectedMovePct", () => {
  const forecast: ForecastDay[] = [
    { date: "2026-09-17", predicted: 100, lower: 90, upper: 110 },
    { date: "2026-09-18", predicted: 110, lower: 95, upper: 125 },
  ];

  test("measures against the last forecast row", () => {
    expect(expectedMovePct(forecast, 100)).toBeCloseTo(10);
    expect(expectedMovePct(forecast, 110)).toBeCloseTo(0);
  });

  test("returns null without inputs", () => {
    expect(expectedMovePct(null, 100)).toBeNull();
    expect(expectedMovePct(forecast, null)).toBeNull();
    expect(expectedMovePct([], 100)).toBeNull();
  });
});
