import axios from "axios";
import type {
  ApiErrorBody,
  ConfidenceResponse,
  DailyReport,
  Forecaster,
  HistoryResponse,
  JournalResponse,
  NewsItem,
  PredictResponse,
  PriceHistoryResponse,
  ScoreboardResponse,
} from "../types";

/** Axios instance → FastAPI backend (uvicorn on :8000 by default). */
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
  timeout: 120_000, // predictions can be slow on CPU (Prophet / FinBERT load)
});

/** Extract FastAPI's { detail } error body into a human message. */
export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError<ApiErrorBody>(err)) {
    return err.response?.data?.detail || err.message || "Request failed";
  }
  if (err instanceof Error) return err.message;
  return "Request failed";
}

/* --------------------------------- endpoints --------------------------------- */

export async function predict(
  coinId: string,
  days: number,
  forecaster: Forecaster
): Promise<PredictResponse> {
  const res = await apiClient.get(`/predict/${coinId}`, {
    params: { days, forecaster },
  });
  return res.data;
}

export async function getConfidence(coinId: string): Promise<ConfidenceResponse> {
  const res = await apiClient.get(`/confidence/${coinId}`);
  return res.data;
}

export async function getNews(coinId: string): Promise<NewsItem[]> {
  const res = await apiClient.get(`/news/${coinId}`);
  return res.data.news ?? [];
}

export async function getHistory(coinId: string): Promise<HistoryResponse> {
  const res = await apiClient.get(`/history/${coinId}`);
  return res.data;
}

export async function getDailyReport(): Promise<DailyReport> {
  const res = await apiClient.get(`/research/daily-report`);
  return res.data;
}

export async function getScoreboard(): Promise<ScoreboardResponse> {
  const res = await apiClient.get(`/research/scoreboard`);
  return res.data;
}

export async function getJournal(): Promise<JournalResponse> {
  const res = await apiClient.get(`/research/journal`);
  return res.data;
}

export async function getPriceHistory(
  coinId: string,
  days = 90
): Promise<PriceHistoryResponse> {
  const res = await apiClient.get(`/prices/${coinId}`, {
    params: { days },
  });
  return res.data;
}
