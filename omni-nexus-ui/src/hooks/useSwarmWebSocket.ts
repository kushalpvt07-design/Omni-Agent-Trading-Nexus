"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { PortfolioData, CheckpointDetails, AgentNodeId, AgentStepTelemetry } from "@/types/swarm";

export interface LogMessage {
  type: "user" | "status" | "message" | "checkpoint";
  role?: string;
  content: string;
  timestamp: string;
}

const INITIAL_AGENT_STEPS: Record<AgentNodeId, AgentStepTelemetry> = {
  parser_node: { id: "parser_node", label: "Parser Agent", shortRole: "NLP Extract", status: "idle" },
  quant_agent_node: { id: "quant_agent_node", label: "Quant MCP", shortRole: "Volatility & RSI", status: "idle" },
  sentiment_agent_node: { id: "sentiment_agent_node", label: "Sentiment MCP", shortRole: "News Polarity", status: "idle" },
  orchestrator_node: { id: "orchestrator_node", label: "Orchestrator", shortRole: "65/35 Synthesis", status: "idle" },
  risk_agent_node: { id: "risk_agent_node", label: "Risk Desk", shortRole: "Vol-Target Gate", status: "idle" },
  execution_agent_node: { id: "execution_agent_node", label: "Execution Engine", shortRole: "Alpaca & Ledger", status: "idle" },
};

export interface SwarmUIState {
  isConnected: boolean;
  isDeploying: boolean;
  directiveLogs: LogMessage[];
  assetData: any | null;
  sentimentData: any | null;
  portfolioData: PortfolioData | null;
  pendingCheckpoint: CheckpointDetails | null;
  agentSteps: Record<AgentNodeId, AgentStepTelemetry>;
}

function detectNodeFromStatus(text: string): AgentNodeId | null {
  const lower = text.toLowerCase();
  if (lower.includes("parser")) return "parser_node";
  if (lower.includes("quant")) return "quant_agent_node";
  if (lower.includes("sentiment")) return "sentiment_agent_node";
  if (lower.includes("orchestrator")) return "orchestrator_node";
  if (lower.includes("risk")) return "risk_agent_node";
  if (lower.includes("execution")) return "execution_agent_node";
  return null;
}

export function useSwarmWebSocket(wsBaseUrl: string, token?: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const stepTimestampsRef = useRef<Record<string, number>>({});

  const [state, setState] = useState<SwarmUIState>({
    isConnected: false,
    isDeploying: false,
    directiveLogs: [],
    assetData: null,
    sentimentData: null,
    portfolioData: null,
    pendingCheckpoint: null,
    agentSteps: INITIAL_AGENT_STEPS,
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
          const nowPerf = performance.now();

          if (msg.type === "status") {
            const nodeId = (msg.node as AgentNodeId) || detectNodeFromStatus(msg.content || "");
            setState((prev) => {
              const nextSteps = { ...prev.agentSteps };
              if (nodeId && nextSteps[nodeId]) {
                const startTs = stepTimestampsRef.current[nodeId] || stepTimestampsRef.current["last"] || nowPerf;
                const fallbackElapsed = Math.max(18, Math.round(nowPerf - startTs));
                const exactLatency =
                  typeof msg.latency_ms === "number"
                    ? Math.round(msg.latency_ms)
                    : fallbackElapsed;
                stepTimestampsRef.current["last"] = nowPerf;
                nextSteps[nodeId] = {
                  ...nextSteps[nodeId],
                  status: "completed",
                  latencyMs: exactLatency,
                };
                if (nodeId === "parser_node") {
                  stepTimestampsRef.current["quant_agent_node"] = nowPerf;
                  stepTimestampsRef.current["sentiment_agent_node"] = nowPerf;
                  nextSteps.quant_agent_node = { ...nextSteps.quant_agent_node, status: "running" };
                  nextSteps.sentiment_agent_node = { ...nextSteps.sentiment_agent_node, status: "running" };
                } else if (nodeId === "quant_agent_node" || nodeId === "sentiment_agent_node") {
                  if (
                    nextSteps.quant_agent_node.status === "completed" &&
                    nextSteps.sentiment_agent_node.status === "completed"
                  ) {
                    stepTimestampsRef.current["orchestrator_node"] = nowPerf;
                    nextSteps.orchestrator_node = { ...nextSteps.orchestrator_node, status: "running" };
                  }
                } else if (nodeId === "orchestrator_node") {
                  stepTimestampsRef.current["risk_agent_node"] = nowPerf;
                  nextSteps.risk_agent_node = { ...nextSteps.risk_agent_node, status: "running" };
                }
              }
              return {
                ...prev,
                agentSteps: nextSteps,
                directiveLogs: [
                  ...prev.directiveLogs,
                  { type: "status", role: msg.role, content: msg.content, timestamp: nowIso },
                ],
              };
            });
          } else if (msg.type === "message") {
            const isClosing =
              msg.content === "Transaction cycle closed." ||
              msg.role === "SYSTEM ERROR";
            const roleNode = detectNodeFromStatus(msg.role || "");

            setState((prev) => {
              const nextSteps = { ...prev.agentSteps };
              if (roleNode) {
                nextSteps[roleNode] = {
                  ...nextSteps[roleNode],
                  status: msg.role === "SYSTEM ERROR" ? "error" : "completed",
                  lastOutput: msg.content,
                };
              }
              if (msg.role === "Execution Hub") {
                nextSteps.execution_agent_node = {
                  ...nextSteps.execution_agent_node,
                  status: "completed",
                  lastOutput: msg.content,
                };
              }
              return {
                ...prev,
                isDeploying: isClosing ? false : prev.isDeploying,
                agentSteps: nextSteps,
                directiveLogs: [
                  ...prev.directiveLogs,
                  { type: "message", role: msg.role, content: msg.content, timestamp: nowIso },
                ],
              };
            });
          } else if (msg.type === "asset_intelligence") {
            setState((prev) => ({
              ...prev,
              assetData: msg.data,
              agentSteps: {
                ...prev.agentSteps,
                quant_agent_node: {
                  ...prev.agentSteps.quant_agent_node,
                  lastOutput: JSON.stringify(
                    {
                      ticker: msg.data?.ticker,
                      current_price: msg.data?.current_price,
                      thirty_day_sma: msg.data?.thirty_day_sma,
                      rsi_14: msg.data?.rsi_14,
                      volatility_pct: msg.data?.volatility,
                      volume_ratio_30d: msg.data?.volume_ratio_30d,
                    },
                    null,
                    2
                  ),
                },
              },
            }));
          } else if (msg.type === "sentiment_data") {
            setState((prev) => ({
              ...prev,
              sentimentData: { ...(prev.sentimentData || {}), ...msg.data },
              agentSteps: {
                ...prev.agentSteps,
                sentiment_agent_node: {
                  ...prev.agentSteps.sentiment_agent_node,
                  lastOutput: JSON.stringify(
                    {
                      sentiment_label: msg.data?.sentiment_label,
                      sentiment_score: msg.data?.sentiment_score,
                      headlines_count: msg.data?.top_headlines?.length || 0,
                    },
                    null,
                    2
                  ),
                },
              },
            }));
          } else if (msg.type === "checkpoint") {
            setState((prev) => ({
              ...prev,
              pendingCheckpoint: msg.trade_details || null,
              agentSteps: {
                ...prev.agentSteps,
                execution_agent_node: {
                  ...prev.agentSteps.execution_agent_node,
                  status: "running",
                  lastOutput: "Paused at Human-in-the-Loop checkpoint awaiting authorization.",
                },
              },
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
    const nowPerf = performance.now();
    stepTimestampsRef.current = { parser_node: nowPerf, last: nowPerf };

    setState((prev) => ({
      ...prev,
      isDeploying: true,
      pendingCheckpoint: null,
      agentSteps: {
        ...INITIAL_AGENT_STEPS,
        parser_node: {
          ...INITIAL_AGENT_STEPS.parser_node,
          status: "running",
          lastOutput: `Directive: "${directive}"`,
        },
      },
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
      agentSteps: {
        ...prev.agentSteps,
        execution_agent_node: {
          ...prev.agentSteps.execution_agent_node,
          status: approved ? "completed" : "error",
          lastOutput: approved ? "Authorized by user — order dispatched." : "Cancelled by user at HITL gate.",
        },
      },
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
