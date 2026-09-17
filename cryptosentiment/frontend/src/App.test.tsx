import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

/* ---- mock the API layer (no network in tests) ---- */
jest.mock("./services/api", () => ({
  apiErrorMessage: (e: unknown) =>
    e instanceof Error ? e.message : "Request failed",
  getDailyReport: jest.fn(() =>
    Promise.resolve({
      date: "2026-09-16",
      summary: {},
      deltas: {
        price: { settled: "--", expectancy: "--" },
        info: { settled: "--", expectancy: "--" },
        vetoes: "--",
      },
      per_coin: {
        bitcoin: {
          signal_price: "HOLD",
          signal_info: "HOLD",
          vetoed: false,
          conf_price: 65.8,
          conf_info: 64.7,
          band_position: "inside",
          sentiment: { n: 100, pos: 19, neg: 11, neu: 70 },
          watch: "inside: -3.2% day reaches BUY zone",
        },
      },
      settling_tomorrow: {},
      maturity: { settled_slowest_arm: 0, required_per_arm: 30, to_go: 30 },
    })
  ),
  getScoreboard: jest.fn(() =>
    Promise.resolve({ settled_rows: 0, note: "no settled signals yet" })
  ),
  predict: jest.fn(() =>
    Promise.resolve({
      prediction: [
        { date: "2026-09-17", predicted: 100, lower: 90, upper: 110 },
      ],
      confidence: 62.5,
      db_id: 1,
      forecaster: "naive",
      history_rows: 365,
      news_articles: 40,
    })
  ),
  getConfidence: jest.fn(() =>
    Promise.resolve({
      confidence: "62.50%",
      sentiments_analyzed: 40,
      volatility_score: 0.03,
      note: "Heuristic score.",
    })
  ),
  getNews: jest.fn(() =>
    Promise.resolve([
      { label: "POSITIVE", score: 0.91, text: "BTC holds above $60k" },
      { label: "NEGATIVE", score: 0.77, text: "Exchange outflows spike" },
    ])
  ),
  getHistory: jest.fn(() => Promise.resolve({ predictions: [] })),
  getJournal: jest.fn(() =>
    Promise.resolve({
      rows: [
        {
          date: "2026-09-16",
          coin_id: "bitcoin",
          price: 75841,
          band_position: "inside",
          signal_price: "HOLD",
          signal_info: "HOLD",
          conf_price: 65.76,
          conf_info: null,
          net_price: null,
          net_info: null,
          win_price: null,
          win_info: null,
        },
      ],
      summary: { settled_rows: 0, note: "no settled signals yet" },
    })
  ),
  getPriceHistory: jest.fn(() =>
    Promise.resolve({
      coin_id: "bitcoin",
      days: 90,
      prices: [
        [1758000000000, 75000],
        [1758086400000, 76270],
      ],
    })
  ),
}));

test("renders the research terminal shell with top bar and tabs", async () => {
  render(<App />);

  // Brand wordmark (the footer also mentions the name, so query the heading role)
  expect(screen.getByTitle("CryptoSentiment Research Terminal")).toBeInTheDocument();

  // Section tabs
  expect(screen.getByRole("tab", { name: "Forecast" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Sentiment" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Research" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "History" })).toBeInTheDocument();

  // Coin picker defaults to Bitcoin
  await waitFor(() => {
    expect(screen.getByDisplayValue("bitcoin")).toBeInTheDocument();
  });

  // Default tab is Forecast; wait for the engine panel to appear
  await waitFor(() => {
    expect(screen.getByText(/forecast engine/i)).toBeInTheDocument();
  });
});

test("research tab shows E006 scoreboard with no settled signals", async () => {
  render(<App />);

  await waitFor(() => {
    expect(screen.getByText(/forecast engine/i)).toBeInTheDocument();
  });

  // Switch to Research tab
  await userEvent.click(screen.getByRole("tab", { name: "Research" }));

  expect(
    await screen.findByText(/E006 · Dual-Arm Live Scoreboard/i)
  ).toBeInTheDocument();
  expect(
    await screen.findByText(/no settled signals yet/i)
  ).toBeInTheDocument();
  expect(screen.getByText("Today's Dual-Arm Signals")).toBeInTheDocument();
});
