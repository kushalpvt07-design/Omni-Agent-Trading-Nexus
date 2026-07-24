"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

export interface LogMessage {
  id: string;
  role: string;
  content: string;
  type?: "user" | "status" | "message" | "checkpoint";
  timestamp: string;
}

export interface SwarmState {
  isConnected: boolean;
  isDeploying: boolean;
  activeAgent: 'idle' | 'parser' | 'sentiment' | 'quant' | 'orchestrator' | 'risk' | 'action_center';
  chartData: any[];
  assetData: any | null;
  directiveLogs: LogMessage[];
  newsIntel: { headline: string; quantImpact: 'High' | 'Med' | 'Low'; score: number; }[];
  pipelineStatus: {
    parser: 'pending' | 'active' | 'complete' | 'error';
    sentiment: 'pending' | 'active' | 'complete' | 'error';
    quant: 'pending' | 'active' | 'complete' | 'error';
    orchestrator: 'pending' | 'active' | 'complete' | 'error';
    risk: 'pending' | 'active' | 'complete' | 'error';
  };
  pendingAction: null | {
    ticker: string;
    action: string;
    allocation: number;
    shares: number;
  };
}

export function useSwarmWebSocket(url: string) {
  const [state, setState] = useState<SwarmState>({
    isConnected: false,
    isDeploying: false,
    activeAgent: 'idle',
    chartData: [],
    assetData: null,
    directiveLogs: [],
    newsIntel: [],
    pipelineStatus: {
      parser: 'pending',
      sentiment: 'pending',
      quant: 'pending',
      orchestrator: 'pending',
      risk: 'pending',
    },
    pendingAction: null,
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initialize the WebSocket to your FastAPI backend
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(prev => ({ ...prev, isConnected: true }));
      console.log("Omni-Agent Nexus: WebSocket Connected.");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        // Handle LangGraph node transitions
        if (payload.type === 'node_update') {
          setState(prev => ({
            ...prev,
            pipelineStatus: {
              ...prev.pipelineStatus,
              [payload.node]: payload.status
            }
          }));
        }

        // Handle Human-in-the-loop checkpoint
        if (payload.type === 'checkpoint') {
          setState(prev => ({
            ...prev,
            isDeploying: false,
            activeAgent: 'action_center',
            pendingAction: payload.trade_details || { ticker: 'PENDING', action: 'REVIEW', allocation: 0, shares: 0 }
          }));
        }

        // Handle Chart Data
        if (payload.type === 'chart_data') {
          setState(prev => ({
            ...prev,
            chartData: payload.data || []
          }));
        }

        // Handle Asset Intelligence
        if (payload.type === 'asset_intelligence') {
          setState(prev => ({
            ...prev,
            assetData: payload.data || null
          }));
        }

        // General logging for anything with content
        if (payload.content) {
          const timeString = new Date().toLocaleTimeString();
          const newLog: LogMessage = {
            id: Math.random().toString(36).substring(2, 9),
            role: payload.role || "SYSTEM",
            content: payload.content,
            type: payload.type || "message",
            timestamp: timeString,
          };
          setState(prev => ({
            ...prev,
            directiveLogs: [...prev.directiveLogs, newLog]
          }));

          // THE FIX: Catch the early termination or the HITL checkpoint
          if (
              typeof payload.content === 'string' && (
                payload.content.includes("Swarm pipeline execution cycle finished") || 
                payload.content.includes("Pipeline reached Human-in-the-Loop checkpoint")
              )
          ) {
              setState(prev => ({ ...prev, isDeploying: false }));
          }
        }

        // Handle raw system logs (Pipeline status updates)
        if (payload.type === 'message') {
          const roleMap: Record<string, keyof SwarmState['pipelineStatus']> = {
            'Parser': 'parser',
            'Sentiment': 'sentiment',
            'Quant': 'quant',
            'Orchestrator': 'orchestrator',
            'Risk': 'risk'
          };
          const node = roleMap[payload.role];
          
          setState(prev => {
            let nextAgent: SwarmState['activeAgent'] = prev.activeAgent;
            if (payload.role === 'Parser') nextAgent = 'sentiment';
            else if (payload.role === 'Sentiment') nextAgent = 'quant';
            else if (payload.role === 'Quant') nextAgent = 'orchestrator';
            else if (payload.role === 'Orchestrator') nextAgent = 'risk';
            else if (payload.role === 'Risk') nextAgent = 'action_center';

            return {
              ...prev,
              activeAgent: nextAgent,
              pipelineStatus: node ? { ...prev.pipelineStatus, [node]: 'complete' as const } : prev.pipelineStatus
            };
          });
        }
      } catch (error) {
        console.error("Critical failure: The FastAPI backend sent malformed JSON.", error);
      }
    };

    ws.onclose = () => {
      setState(prev => ({ ...prev, isConnected: false }));
      console.warn("Omni-Agent Nexus: WebSocket Disconnected.");
    };

    return () => {
      ws.close();
    };
  }, [url]);

  // Command execution handlers
  const deployDirective = useCallback((directive: string) => {
    if (!directive.trim()) return;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // Optimistic state updates
      const timeString = new Date().toLocaleTimeString();
      const newLog: LogMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: "USER",
        content: directive,
        type: "user",
        timestamp: timeString,
      };

      setState(prev => ({
        ...prev,
        isDeploying: true,
        activeAgent: 'parser',
        directiveLogs: [...prev.directiveLogs, newLog],
        chartData: [] // reset chart data
      }));
      
      wsRef.current.send(JSON.stringify({ directive: directive, paper_trading: true }));
    } else {
      console.error("Cannot deploy: Nexus is offline.");
    }
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && state.pendingAction) {
      wsRef.current.send(JSON.stringify({ 
        type: 'human_approval', 
        approved: approved 
      }));
      // Clear the action center once resolved
      setState(prev => ({ ...prev, pendingAction: null }));
    }
  }, [state.pendingAction]);

  return { state, deployDirective, resolveCheckpoint };
}
