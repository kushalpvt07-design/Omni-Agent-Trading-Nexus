export interface PositionItem {
  ticker: string;
  shares: number;
  current_price: number;
  avg_cost: number;
  market_value: number;
}

export interface PortfolioData {
  cash: number;
  total_value: number;
  positions: PositionItem[];
}

export interface PortfolioHistoryPoint {
  timestamp: string;
  total_value: number;
  cash: number;
}

export interface PortfolioChange {
  start_value: number;
  current_value: number;
  change_amount: number;
  change_pct: number;
}

export interface PortfolioHistory {
  timeframe: "1D" | "1M" | "1Y" | "ALL";
  data_points: PortfolioHistoryPoint[];
  change: PortfolioChange | null;
}

export interface CheckpointDetails {
  ticker: string;
  action: string;
  allocation: number | string;
  shares: number | string;
}
