import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000",
});

export const predictPrices = async (coinId: string, days: number = 7) => {
  const res = await apiClient.get(`/predict/${coinId}?days=${days}`);
  return res.data.prediction;
};

export const getConfidenceScore = async (coinId: string) => {
  const res = await apiClient.get(`/confidence/${coinId}`);
  return res.data.confidence;
};

export const getPredictionHistory = async (coinId: string) => {
  const res = await apiClient.get(`/history/${coinId}`);
  return res.data.predictions || [];
};

export const getNewsSentiment = async (coinId: string) => {
  const res = await apiClient.get(`/news/${coinId}`);
  return res.data.news || [];
};