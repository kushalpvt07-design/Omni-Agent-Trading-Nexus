/**
 * API utility for the Next.js frontend to communicate with the FastAPI backend.
 * All sensitive keys (e.g., Alpaca API) reside exclusively in the backend.
 *
 * The primary real-time channel is the WebSocket in useSwarmWebSocket.ts.
 * This file handles the stateless REST endpoint for one-shot analysis.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AnalyzeRequest {
  directive: string;
  paper_trading?: boolean;
}

export interface AnalyzeResponse {
  status: string;
  ticker?: string;
  action?: "BUY" | "SELL" | "HOLD" | "REJECT";
  shares?: number;
  risk_approved?: boolean;
  orchestrator_reasoning?: string;
  error_message?: string;
}

/**
 * Sends a natural-language trading directive to the stateless analysis endpoint.
 * Returns the swarm's synthesized decision without executing any trade.
 */
export async function submitAnalysis(
  request: AnalyzeRequest
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      directive: request.directive,
      paper_trading: request.paper_trading ?? true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Backend rejected directive: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Health check — useful for connection status indicators.
 */
export async function checkHealth(): Promise<{
  status: string;
  version: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error("Backend health check failed");
  }
  return response.json();
}
