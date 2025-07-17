import React, { useState } from 'react';
import './App.css';
import './styles/tailwind.css';
import { useTheme } from './lib/theme';

// Components
import Sidebar from './components/Sidebar';
import PredictionChart from './components/Dashboard/PredictionChart';
import ConfidenceMeter from './components/Dashboard/ConfidenceMeter';
import NewsSentimentPanel from './components/Dashboard/NewsSentiment';
import MetricCard from './components/Dashboard/MetricCard';
import PredictionHistoryTable from './components/Dashboard/PredictionHistoryTable';

// API Service
import {
  predictPrices,
  getConfidenceScore,
  getPredictionHistory,
  getNewsSentiment
} from './services/api.service';

function App() {
  const { theme, } = useTheme();
  const [coin, setCoin] = useState('bitcoin');
  const [prediction, setPrediction] = useState<any>(null);
  const [confidence, setConfidence] = useState<string>('0%');
  const [news, setNews] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchPrediction = async () => {
    setLoading(true);
    try {
      const result = await predictPrices(coin, 7);
      const chartData = result.map((p: any) => ({
        name: p.date,
        Predicted: p.predicted,
        Lower: p.lower,
        Upper: p.upper,
      }));
      setPrediction(chartData);
    } catch (err) {
      console.error("Failed to fetch prediction:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchConfidence = async () => {
    setLoading(true);
    try {
      const score = await getConfidenceScore(coin);
      setConfidence(score);
    } catch (err) {
      console.error("Failed to fetch confidence:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchNews = async () => {
    setLoading(true);
    try {
      const newsData = await getNewsSentiment(coin);
      setNews(newsData);
    } catch (err) {
      console.error("Failed to load news:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const historyData = await getPredictionHistory(coin);
      setHistory(historyData);
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setLoading(false);
    }
  };

  const sentimentData = [
    { name: 'Positive', value: news.filter(n => n.label === 'POSITIVE').length },
    { name: 'Negative', value: news.filter(n => n.label === 'NEGATIVE').length },
  ];

  return (
    <div className="flex min-h-screen bg-background text-foreground transition-colors duration-300 ease-in-out">

      {/* Sidebar */}
      <Sidebar coin={coin} setCoin={setCoin} />

      {/* Main Dashboard */}
      <div className="flex-1 p-6 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <MetricCard title="Current Price" value="109543.89" change="+2.35%" />
          <MetricCard title="Sentiment Score" value="+7.8" change="Positive" />
        </div>

        <div className="flex flex-wrap gap-2 mb-6">
          <button onClick={fetchPrediction} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-md">
            {loading ? 'Loading...' : 'Get Price Prediction'}
          </button>

          <button onClick={fetchConfidence} disabled={loading} className="px-4 py-2 border border-input rounded-md hover:bg-accent">
            Get Confidence Score
          </button>

          <button onClick={fetchNews} disabled={loading} className="px-4 py-2 border border-input rounded-md hover:bg-accent">
            {loading ? 'Loading...' : 'Load Latest News'}
          </button>

          <button onClick={fetchHistory} disabled={loading} className="px-4 py-2 border border-input rounded-md hover:bg-accent">
            Load Prediction History
          </button>
        </div>

        {loading && <p>Loading... please wait</p>}

        {prediction && prediction.length > 0 ? (
  <PredictionChart data={prediction} />
) : (
  <p>No prediction data available. Try clicking "Get Price Prediction"</p>
)}
        <ConfidenceMeter confidence={confidence} />

        {news.length > 0 && <NewsSentimentPanel news={news} />}
        {history.length > 0 && <PredictionHistoryTable predictions={history} />}
      </div>
    </div>
  );
}

export default App;