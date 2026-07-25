"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export interface LogMessage {
  id: string;
  type: "user" | "message" | "status" | "checkpoint" | "error";
  role?: string;
  content: string;
  timestamp: string;
}

export interface SwarmState {
  isConnected: boolean;
  isDeploying: boolean;
  directiveLogs: LogMessage[];
  assetData: any | null;
  sentimentData: any | null;
  pendingCheckpoint: any | null;
}

export function useSwarmWebSocket(url: string) {
  const [state, setState] = useState<SwarmState>({
    isConnected: false,
    isDeploying: false,
    directiveLogs: [],
    assetData: null,
    sentimentData: null,
    pendingCheckpoint: null,
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setState((prev) => ({ ...prev, isConnected: true }));
      };

      ws.onclose = () => {
        setState((prev) => ({ ...prev, isConnected: false }));
      };

      ws.onerror = (err) => {
        console.error("WebSocket connection error:", err);
        setState((prev) => ({ ...prev, isConnected: false }));
      };

      ws.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          const timeStr = new Date().toLocaleTimeString();

          if (packet.type === "asset_intelligence") {
            setState((prev) => ({ ...prev, assetData: packet.data }));
          } else if (packet.type === "sentiment_data") {
            setState((prev) => ({ ...prev, sentimentData: packet.data }));
          } else if (packet.type === "checkpoint") {
            setState((prev) => ({
              ...prev,
              isDeploying: false,
              pendingCheckpoint: packet.trade_details,
              directiveLogs: [
                ...prev.directiveLogs,
                { id: crypto.randomUUID(), type: "checkpoint", role: "SYSTEM", content: packet.content, timestamp: timeStr },
              ],
            }));
          } else if (packet.type === "status" || packet.type === "message") {
            const isDone = packet.content?.includes("cycle finished");
            setState((prev) => ({
              ...prev,
              isDeploying: isDone ? false : prev.isDeploying,
              directiveLogs: [
                ...prev.directiveLogs,
                { id: crypto.randomUUID(), type: packet.type, role: packet.role, content: packet.content, timestamp: timeStr },
              ],
            }));
          }
        } catch (err) {
          console.error("Failed to parse WebSocket transmission:", err);
        }
      };
    } catch (e) {
      console.error("Failed to instantiate WebSocket:", e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const deployDirective = useCallback((directive: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const timeStr = new Date().toLocaleTimeString();
    const userLog: LogMessage = {
      id: crypto.randomUUID(),
      type: "user",
      role: "USER",
      content: directive,
      timestamp: timeStr,
    };

    setState((prev) => ({
      ...prev,
      isDeploying: true,
      pendingCheckpoint: null,
      directiveLogs: [...prev.directiveLogs, userLog],
    }));

    wsRef.current.send(JSON.stringify({ directive, paper_trading: true }));
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(
      JSON.stringify({ type: "human_approval", approved })
    );

    setState((prev) => ({ ...prev, pendingCheckpoint: null, isDeploying: true }));
  }, []);

  return { state, deployDirective, resolveCheckpoint };
}
