import { useState, useEffect, useRef, useCallback } from "react";
import type {
  AssetData,
  SentimentData,
  CheckpointData,
  LogMessage,
  SwarmState,
} from "@/types/swarm";

// Re-export for backward compatibility with existing component imports
export type { LogMessage } from "@/types/swarm";

const RECONNECT_INTERVAL_MS = 2000;
const MAX_RECONNECT_DELAY_MS = 30000;

export function useSwarmWebSocket(url: string, token?: string) {
  const [state, setState] = useState<SwarmState>({
    isConnected: false,
    isDeploying: false,
    directiveLogs: [],
    assetData: null,
    sentimentData: null,
    pendingCheckpoint: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);

  const connect = useCallback(() => {
    // Prevent duplicate connections
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    // Append auth token as query parameter if provided
    const authUrl = token ? `${url}?token=${encodeURIComponent(token)}` : url;
    const ws = new WebSocket(authUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptRef.current = 0;
      setState((prev) => ({ ...prev, isConnected: true }));
    };

    ws.onclose = () => {
      setState((prev) => ({
        ...prev,
        isConnected: false,
        isDeploying: false,
      }));

      // Auto-reconnect with exponential backoff (unless intentionally closed)
      if (!intentionalCloseRef.current) {
        const delay = Math.min(
          RECONNECT_INTERVAL_MS * Math.pow(2, reconnectAttemptRef.current),
          MAX_RECONNECT_DELAY_MS
        );
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // Let onclose handle reconnection — just close the broken socket
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === "asset_intelligence") {
          setState((prev) => ({
            ...prev,
            assetData: payload.data as AssetData,
          }));
        }

        if (payload.type === "sentiment_data") {
          setState((prev) => ({
            ...prev,
            sentimentData: {
              ...prev.sentimentData,
              ...payload.data,
            } as SentimentData,
          }));
        }

        // Standard terminal logs
        if (payload.type === "message" || payload.type === "status") {
          setState((prev) => ({
            ...prev,
            directiveLogs: [...prev.directiveLogs, payload as LogMessage],
          }));

          if (
            payload.content &&
            payload.content.includes("Transaction cycle closed.")
          ) {
            setState((prev) => ({ ...prev, isDeploying: false }));
          }
        }

        // Pipeline completed without checkpoint (no HITL needed)
        if (payload.type === "pipeline_complete") {
          setState((prev) => ({
            ...prev,
            isDeploying: false,
            directiveLogs: [...prev.directiveLogs, payload as LogMessage],
          }));
        }

        if (payload.type === "checkpoint") {
          setState((prev) => ({
            ...prev,
            pendingCheckpoint: payload.trade_details as CheckpointData,
          }));
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };
  }, [url, token]);

  useEffect(() => {
    intentionalCloseRef.current = false;
    connect();

    return () => {
      intentionalCloseRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const deployDirective = useCallback((directive: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const userEchoLog: LogMessage = {
        type: "message",
        role: "user",
        content: `> ${directive}`,
        timestamp: new Date().toISOString(),
      };

      setState((prev) => ({
        ...prev,
        isDeploying: true,
        directiveLogs: [userEchoLog],
        assetData: null,
        sentimentData: null,
        pendingCheckpoint: null,
      }));

      wsRef.current.send(JSON.stringify({ directive, paper_trading: true }));
    } else {
      console.error("WebSocket is not connected.");
    }
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "human_approval", approved })
      );
      setState((prev) => ({ ...prev, pendingCheckpoint: null }));
    }
  }, []);

  return { state, deployDirective, resolveCheckpoint };
}
