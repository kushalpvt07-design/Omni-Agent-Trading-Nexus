/**
 * Omni-Agent Trading Nexus — Shared TypeScript Interfaces
 *
 * Defines the contract between the FastAPI WebSocket backend and the
 * Next.js frontend.  Every payload shape the backend can emit is
 * represented here so components never touch `any`.
 */

// ---- Asset Intelligence (from utils.py → get_live_asset_data) ----

export interface ChartDataPoint {
  time: string;
  price: number;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
}

export interface AssetData {
  ticker: string;
  current_price: number;
  change_pct: number;
  volatility: number;
  is_positive: boolean;
  chart_data: ChartDataPoint[];
  timeframe_data?: Record<string, ChartDataPoint[]>;
  currency?: string;
}

// ---- Sentiment / Consensus (from sentiment_server.py) ----

export interface SentimentData {
  status?: string;
  ticker?: string;
  sentiment_label?: string;
  sentiment_score?: number;
  top_headlines?: string[];
  reasoning?: string;
}

// ---- Human-in-the-Loop Checkpoint (from main.py WebSocket) ----

export interface CheckpointData {
  ticker: string;
  action: string;
  allocation: number | string;
  shares: number | string;
}

// ---- Portfolio Ledger (from portfolio_ledger.json) ----

export interface PortfolioPosition {
  ticker: string;
  shares: number;
  current_price: number;
  market_value: number;
}

export interface PortfolioData {
  cash: number;
  total_value: number;
  positions: PortfolioPosition[];
}

// ---- WebSocket Log Entry ----

export interface LogMessage {
  id?: string | number;
  type: string;
  role: string;
  content: string;
  timestamp?: string;
}

// ---- Aggregate UI State ----

export interface SwarmState {
  isConnected: boolean;
  isDeploying: boolean;
  directiveLogs: LogMessage[];
  assetData: AssetData | null;
  sentimentData: SentimentData | null;
  pendingCheckpoint: CheckpointData | null;
  portfolioData: PortfolioData | null;
}
