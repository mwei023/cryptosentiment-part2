import React, { useState } from "react";
import { useDashboard } from "./hooks/useDashboard";
import TopBar from "./components/layout/TopBar";
import Tabs, { type TabId } from "./components/layout/Tabs";
import ForecastTab from "./components/Forecast/ForecastTab";
import SentimentTab from "./components/Sentiment/SentimentTab";
import ResearchTab from "./components/Research/ResearchTab";
import HistoryTab from "./components/History/HistoryTab";
import ErrorNote from "./components/ui/ErrorNote";

function App() {
  const {
    coin,
    setCoin,
    report,
    scoreboard,
    journalRows,
    live,
    researchLoading,
    researchError,
    lastRefreshed,
    reloadResearch,
  } = useDashboard();
  const [tab, setTab] = useState<TabId>("forecast");

  return (
    <div className="min-h-screen">
      <TopBar
        coin={coin}
        onCoinChange={setCoin}
        onRefresh={reloadResearch}
        refreshing={researchLoading}
        lastRefreshed={lastRefreshed}
      />

      <main className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:px-6">
        {/* Research-state errors surface here; per-panel errors show inline */}
        {researchError && (
          <ErrorNote
            className="mb-5"
            message={`Research state unavailable: ${researchError}`}
          />
        )}

        <div className="mb-5">
          <Tabs active={tab} onChange={setTab} />
        </div>

        {tab === "forecast" && <ForecastTab coin={coin} live={live} />}
        {tab === "sentiment" && <SentimentTab coin={coin} />}
        {tab === "research" && (
          <ResearchTab
            scoreboard={scoreboard}
            report={report}
            journalRows={journalRows}
          />
        )}
        {tab === "history" && <HistoryTab coin={coin} />}
      </main>

      <footer className="border-t border-surface-line py-6">
        <p className="mx-auto max-w-7xl px-4 text-[11px] leading-relaxed text-ink-dim sm:px-6">
          CryptoSentiment is an experimental research system. Forecasts are
          not financial advice; confidence scores are heuristics, not
          calibrated probabilities. Signals settle against next-day closes
          in a paper journal — no real capital is traded.
        </p>
      </footer>
    </div>
  );
}

export default App;
