import React, { useState, useEffect } from 'react';
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
import ResearchScoreboard from './components/Dashboard/ResearchScoreboard';

// API Service
import {
  predictPrices,
  getConfidenceScore,
  getPredictionHistory,
  getNewsSentiment,
  getDailyReport,
  getResearchScoreboard,
} from './services/api.service';

function App() {
  useTheme();
  const [coin, setCoin] = useState('bitcoin');
  const [forecaster, setForecaster] = useState<'naive' | 'prophet'>('naive');
  const [days, setDays] = useState<number>(1);
  const [prediction, setPrediction] = useState<any>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<string>('0%');
  const [news, setNews] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [scoreboard, setScoreboard] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [currentPrice, setCurrentPrice] = useState<string>('--');

  const fetchPrediction = async () => {
    setLoading(true);
    try {
      const result = await predictPrices(coin, days, forecaster);
      if (result.prediction) {
        const chartData = result.prediction.map((p: any) => ({
          name: p.date,
          Predicted: p.predicted,
          Lower: p.lower,
          Upper: p.upper,
        }));
        setPrediction(chartData);
      }
      setWarning(result.warning || null);
      if (result.confidence) {
        setConfidence(`${result.confidence}%`);
      }
    } catch (err: any) {
      console.error("Failed to fetch prediction:", err);
      const msg = err.response?.data?.detail || err.message || "Prediction failed";
      setWarning(`Error: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchConfidence = async () => {
    setLoading(true);
    try {
      const data = await getConfidenceScore(coin);
      setConfidence(data.confidence || `${data}%`);
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

  const fetchResearchData = async () => {
    try {
      const [repData, scoreData] = await Promise.all([
        getDailyReport().catch(() => null),
        getResearchScoreboard().catch(() => null),
      ]);
      if (repData) {
        setReport(repData);
        const coinData = repData.per_coin?.[coin];
        if (coinData?.price) {
          setCurrentPrice(`$${Number(coinData.price).toLocaleString()}`);
        }
      }
      if (scoreData) {
        setScoreboard(scoreData);
      }
    } catch (err) {
      console.error("Failed to load research data:", err);
    }
  };

  useEffect(() => {
    fetchResearchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coin]);

  const posCount = news.filter((n) => n.label === 'POSITIVE').length;
  const negCount = news.filter((n) => n.label === 'NEGATIVE').length;
  const sentimentSummary =
    news.length > 0
      ? `${posCount} pos / ${negCount} neg`
      : 'No news loaded';

  return (
    <div className="flex min-h-screen bg-background text-foreground transition-colors duration-300 ease-in-out">
      {/* Sidebar */}
      <Sidebar coin={coin} setCoin={setCoin} />

      {/* Main Dashboard */}
      <div className="flex-1 p-6 max-w-5xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-4 border-b border-gray-700">
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">
              CryptoSentiment <span className="text-xs font-mono text-blue-400 bg-blue-900/40 px-2 py-0.5 rounded ml-2">v0.2.0-research</span>
            </h1>
            <p className="text-xs text-gray-400 mt-0.5">
              Empirical forecasting, risk-first execution, and dual-arm information testing.
            </p>
          </div>
          <button
            onClick={fetchResearchData}
            className="mt-3 md:mt-0 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded text-gray-300 transition"
          >
            🔄 Refresh Research State
          </button>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard title="Latest Known Price" value={currentPrice} change={coin.toUpperCase()} />
          <MetricCard title="Sentiment Articles" value={String(news.length)} change={sentimentSummary} />
          <MetricCard title="System Confidence" value={confidence} change="Heuristic score" />
        </div>

        {/* Prediction Controls & Forecaster Selector */}
        <div className="bg-gray-800 p-5 rounded-lg border border-gray-700 space-y-4">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h3 className="font-semibold text-white">Forecasting Engine</h3>
              <p className="text-xs text-gray-400">
                Choose between empirical random-walk volatility bands (validated) or Prophet (experimental).
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Forecaster selector */}
              <div className="flex bg-gray-900 p-1 rounded-md border border-gray-700 text-xs">
                <button
                  onClick={() => setForecaster('naive')}
                  className={`px-3 py-1 rounded font-medium transition ${
                    forecaster === 'naive'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Naive + Vol (Validated)
                </button>
                <button
                  onClick={() => setForecaster('prophet')}
                  className={`px-3 py-1 rounded font-medium transition ${
                    forecaster === 'prophet'
                      ? 'bg-amber-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  Prophet (Experimental)
                </button>
              </div>

              {/* Horizon selector */}
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="bg-gray-900 border border-gray-700 text-xs text-white rounded p-1.5 focus:outline-none"
              >
                <option value={1}>1 Day Horizon (Validated)</option>
                <option value={3}>3 Days (Diffusion)</option>
                <option value={7}>7 Days (Experimental)</option>
              </select>

              <button
                onClick={fetchPrediction}
                disabled={loading}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs rounded transition"
              >
                {loading ? 'Running...' : 'Generate Prediction'}
              </button>
            </div>
          </div>

          {/* Warning Banner */}
          {warning && (
            <div className="bg-amber-950/60 border border-amber-800 text-amber-300 text-xs p-3 rounded">
              ⚠️ {warning}
            </div>
          )}

          {/* Quick fetch buttons */}
          <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-700/60 text-xs">
            <button
              onClick={fetchNews}
              disabled={loading}
              className="px-3 py-1 bg-gray-900 hover:bg-gray-700 border border-gray-700 rounded text-gray-300"
            >
              Load FinBERT News
            </button>
            <button
              onClick={fetchConfidence}
              disabled={loading}
              className="px-3 py-1 bg-gray-900 hover:bg-gray-700 border border-gray-700 rounded text-gray-300"
            >
              Update Confidence Score
            </button>
            <button
              onClick={fetchHistory}
              disabled={loading}
              className="px-3 py-1 bg-gray-900 hover:bg-gray-700 border border-gray-700 rounded text-gray-300"
            >
              Load DB History
            </button>
          </div>
        </div>

        {/* Prediction Chart */}
        {prediction && prediction.length > 0 ? (
          <PredictionChart data={prediction} />
        ) : (
          <div className="bg-gray-800/60 p-6 rounded-lg border border-dashed border-gray-700 text-center text-gray-400 text-sm">
            Click <strong className="text-white">"Generate Prediction"</strong> to run the selected forecasting model.
          </div>
        )}

        {/* E006 Research Scoreboard & Band Watch */}
        <ResearchScoreboard report={report} scoreboard={scoreboard} />

        {/* Supporting Panels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ConfidenceMeter confidence={confidence} />
          {news.length > 0 && <NewsSentimentPanel news={news} />}
        </div>

        {/* History Table */}
        {history.length > 0 && <PredictionHistoryTable predictions={history} />}
      </div>
    </div>
  );
}

export default App;