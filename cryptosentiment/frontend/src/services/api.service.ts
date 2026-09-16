import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
});

export const predictPrices = async (
  coinId: string,
  days: number = 1,
  forecaster: "naive" | "prophet" = "naive"
) => {
  const res = await apiClient.get(`/predict/${coinId}?days=${days}&forecaster=${forecaster}`);
  return res.data;
};

export const getConfidenceScore = async (coinId: string) => {
  const res = await apiClient.get(`/confidence/${coinId}`);
  return res.data;
};

export const getPredictionHistory = async (coinId: string) => {
  const res = await apiClient.get(`/history/${coinId}`);
  return res.data.predictions || [];
};

export const getNewsSentiment = async (coinId: string) => {
  const res = await apiClient.get(`/news/${coinId}`);
  return res.data.news || [];
};

export const getDailyReport = async () => {
  const res = await apiClient.get(`/research/daily-report`);
  return res.data;
};

export const getResearchScoreboard = async () => {
  const res = await apiClient.get(`/research/scoreboard`);
  return res.data;
};