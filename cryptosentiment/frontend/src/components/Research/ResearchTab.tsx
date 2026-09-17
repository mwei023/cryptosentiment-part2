import React from "react";
import type { DailyReport, JournalResponse, ScoreboardResponse } from "../../types";
import ScoreboardPanel from "./ScoreboardPanel";
import SignalWatchTable from "./SignalWatchTable";
import JournalPnl from "./JournalPnl";

const ResearchTab: React.FC<{
  scoreboard: ScoreboardResponse | null;
  report: DailyReport | null;
  journalRows: JournalResponse["rows"];
}> = ({ scoreboard, report, journalRows }) => (
  <div className="space-y-5">
    <ScoreboardPanel scoreboard={scoreboard} report={report} />
    <JournalPnl rows={journalRows} />
    <SignalWatchTable report={report} />
  </div>
);

export default ResearchTab;
