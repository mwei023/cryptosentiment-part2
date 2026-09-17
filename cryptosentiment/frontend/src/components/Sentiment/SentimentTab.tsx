import React from "react";
import Panel from "../ui/Panel";
import NewsFeed from "./NewsFeed";
import ConfidenceCard from "./ConfidenceCard";

const SentimentTab: React.FC<{ coin: string }> = ({ coin }) => (
  <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
    <Panel
      title="FinBERT News Feed"
      subtitle={`ProsusAI/finbert headlines for ${coin}`}
      className="lg:col-span-2"
      bodyClassName="p-5"
    >
      <NewsFeed coin={coin} />
    </Panel>

    <Panel
      title="Confidence Score"
      subtitle="Agreement · volatility · sample size"
    >
      <ConfidenceCard coin={coin} />
    </Panel>
  </div>
);

export default SentimentTab;
