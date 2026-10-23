"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { PortfolioData, CheckpointDetails } from "@/types/swarm";

export interface LogMessage {
  type: "user" | "status" | "message" | "checkpoint";
  role?: string;
  content: string;
  timestamp: string;
}

export interface SwarmUIState {
  isConnected: boolean;
  isDeploying: boolean;
  directiveLogs: LogMessage[];
  assetData: any | null;
  sentimentData: any | null;
  portfolioData: PortfolioData | null;
  pendingCheckpoint: CheckpointDetails | null;
}

export function useSwarmWebSocket(wsBaseUrl: string, token?: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const [state, setState] = useState<SwarmUIState>({
    isConnected: false,
    isDeploying: false,
    directiveLogs: [],
    assetData: null,
    sentimentData: null,
    portfolioData: null,
    pendingCheckpoint: null,
  });

  const fetchInitialPortfolio = useCallback(async (jwtToken: string) => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/portfolio", {
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data: PortfolioData = await res.json();
        setState((prev) => ({ ...prev, portfolioData: data }));
      }
    } catch {
      // Ignore transient initial fetch errors
    }
  }, []);

  useEffect(() => {
    if (!token) return;

    fetchInitialPortfolio(token);

    let isUnmounted = false;

    const connect = () => {
      if (isUnmounted) return;
      const url = `${wsBaseUrl}?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmounted) return;
        setState((prev) => ({ ...prev, isConnected: true }));
      };

      ws.onmessage = (event) => {
        if (isUnmounted) return;
        try {
          const msg = JSON.parse(event.data);
          const nowIso = new Date().toISOString();

          if (msg.type === "status") {
            setState((prev) => ({
              ...prev,
              directiveLogs: [
                ...prev.directiveLogs,
                { type: "status", role: msg.role, content: msg.content, timestamp: nowIso },
              ],
            }));
          } else if (msg.type === "message") {
            const isClosing =
              msg.content === "Transaction cycle closed." ||
              msg.role === "SYSTEM ERROR";
            setState((prev) => ({
              ...prev,
              isDeploying: isClosing ? false : prev.isDeploying,
              directiveLogs: [
                ...prev.directiveLogs,
                { type: "message", role: msg.role, content: msg.content, timestamp: nowIso },
              ],
            }));
          } else if (msg.type === "asset_intelligence") {
            setState((prev) => ({ ...prev, assetData: msg.data }));
          } else if (msg.type === "sentiment_data") {
            setState((prev) => ({
              ...prev,
              sentimentData: { ...(prev.sentimentData || {}), ...msg.data },
            }));
          } else if (msg.type === "checkpoint") {
            setState((prev) => ({
              ...prev,
              pendingCheckpoint: msg.trade_details || null,
              directiveLogs: [
                ...prev.directiveLogs,
                { type: "checkpoint", role: msg.role, content: msg.content, timestamp: nowIso },
              ],
            }));
          } else if (msg.type === "pipeline_complete") {
            setState((prev) => ({
              ...prev,
              isDeploying: false,
              pendingCheckpoint: null,
              directiveLogs: [
                ...prev.directiveLogs,
                { type: "status", role: msg.role, content: msg.content, timestamp: nowIso },
              ],
            }));
          } else if (msg.type === "portfolio_update" && msg.data) {
            // Normalize shape in case positions is ever an object
            const raw = msg.data;
            if (Array.isArray(raw.positions)) {
              setState((prev) => ({ ...prev, portfolioData: raw as PortfolioData }));
            } else {
              fetchInitialPortfolio(token);
            }
          }
        } catch {
          // Ignore malformed WS frames
        }
      };

      ws.onclose = (ev) => {
        if (isUnmounted) return;
        setState((prev) => ({ ...prev, isConnected: false, isDeploying: false }));
        // Do not reconnect on explicit 4003 authentication rejection
        if (ev.code !== 4003) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [wsBaseUrl, token, fetchInitialPortfolio]);

  const deployDirective = useCallback((directive: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setState((prev) => ({
      ...prev,
      isDeploying: true,
      pendingCheckpoint: null,
      directiveLogs: [
        ...prev.directiveLogs,
        {
          type: "user",
          role: "USER",
          content: directive,
          timestamp: new Date().toISOString(),
        },
      ],
    }));
    wsRef.current.send(JSON.stringify({ directive }));
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setState((prev) => ({
      ...prev,
      pendingCheckpoint: null,
      isDeploying: false,
    }));
    wsRef.current.send(
      JSON.stringify({
        type: "human_approval",
        approved: approved === true,
      })
    );
  }, []);

  return { state, deployDirective, resolveCheckpoint };
}
