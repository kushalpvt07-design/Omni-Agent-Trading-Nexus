import { useState, useEffect, useRef, useCallback } from "react";

// EXPORT THE INTERFACE SO YOUR COMPONENTS STOP CRYING
export interface LogMessage {
  id?: string | number;
  type: string;
  role: string;
  content: string;
  timestamp?: string;
}

export function useSwarmWebSocket(url: string) {
  const [state, setState] = useState({
    isConnected: false,
    isDeploying: false,
    directiveLogs: [] as LogMessage[], // STRICTLY TYPED NOW
    assetData: null as any,
    sentimentData: null as any,
    pendingCheckpoint: null as any,
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setState((prev) => ({ ...prev, isConnected: true }));
    ws.onclose = () => setState((prev) => ({ ...prev, isConnected: false, isDeploying: false }));

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === "asset_intelligence") {
          setState((prev) => ({ ...prev, assetData: payload.data }));
        }

        if (payload.type === "sentiment_data") {
          setState((prev) => ({ 
            ...prev, 
            sentimentData: { ...prev.sentimentData, ...payload.data } 
          }));
        }

        // Standard Terminal Logs
        if (payload.type === "message" || payload.type === "status") {
          setState((prev) => ({
            ...prev,
            directiveLogs: [...prev.directiveLogs, payload as LogMessage],
          }));

          if (payload.content && payload.content.includes("Transaction cycle closed.")) {
             setState((prev) => ({ ...prev, isDeploying: false }));
          }
        }

        if (payload.type === "checkpoint") {
          setState((prev) => ({ ...prev, pendingCheckpoint: payload.trade_details }));
        }

      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const deployDirective = useCallback((directive: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setState((prev) => ({
        ...prev,
        isDeploying: true,
        directiveLogs: [],
        assetData: null,
        sentimentData: null,
        pendingCheckpoint: null
      }));

      wsRef.current.send(JSON.stringify({ directive, paper_trading: true }));
    } else {
      console.error("WebSocket is not connected.");
    }
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "human_approval", approved }));
      setState((prev) => ({ ...prev, pendingCheckpoint: null }));
    }
  }, []);

  return { state, deployDirective, resolveCheckpoint };
}
