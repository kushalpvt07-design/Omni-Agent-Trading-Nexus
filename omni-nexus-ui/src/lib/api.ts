/**
 * API utility for Next.js frontend to communicate with the FastAPI backend.
 * ALL sensitive keys (e.g., Alpaca API) must reside in the backend.
 * 
 * Note: Streaming the live Swarm Consensus feed requires a streaming protocol 
 * like Server-Sent Events (SSE) or WebSockets. This file handles standard REST.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface TradeDirective {
  ticker: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  quantity?: number;
}

/**
 * Sends a trading directive to the FastAPI backend.
 */
export async function submitTradingDirective(directive: TradeDirective) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(directive),
    });

    if (!response.ok) {
      throw new Error(`Backend rejected directive: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to submit trading directive:", error);
    throw error;
  }
}

/**
 * Initiates an SSE connection for the live Swarm Consensus feed.
 */
export function connectSwarmFeed(onMessage: (data: string) => void, onError: (err: Event) => void): EventSource {
  const eventSource = new EventSource(`${API_BASE_URL}/api/swarm/feed`);
  
  eventSource.onmessage = (event) => {
    onMessage(event.data);
  };

  eventSource.onerror = (error) => {
    onError(error);
  };

  return eventSource;
}
