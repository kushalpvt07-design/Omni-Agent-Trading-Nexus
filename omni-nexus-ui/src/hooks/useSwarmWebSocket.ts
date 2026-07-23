"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

// Define the strict schemas your parser is supposed to be sending
export interface SwarmState {
  isConnected: boolean;
  isDeploying: boolean;
  activeAgent: 'idle' | 'parser' | 'sentiment' | 'quant' | 'orchestrator' | 'risk' | 'action_center';
  chartData: any[];
  directiveLogs: string[];
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

        // Handle raw system logs
        if (payload.type === 'message') {
          const roleMap: Record<string, keyof SwarmState['pipelineStatus']> = {
            'Parser': 'parser',
            'Sentiment': 'sentiment',
            'Quant': 'quant',
            'Orchestrator': 'orchestrator',
            'Risk': 'risk'
          };
          const node = roleMap[payload.role];
          
          let nextAgent: SwarmState['activeAgent'] = prev.activeAgent;
          if (payload.role === 'Parser') nextAgent = 'sentiment';
          else if (payload.role === 'Sentiment') nextAgent = 'quant';
          else if (payload.role === 'Quant') nextAgent = 'orchestrator';
          else if (payload.role === 'Orchestrator') nextAgent = 'risk';
          else if (payload.role === 'Risk') nextAgent = 'action_center';

          setState(prev => ({
            ...prev,
            activeAgent: nextAgent,
            directiveLogs: [...prev.directiveLogs, `[${payload.role}] ${payload.content}`],
            pipelineStatus: node ? { ...prev.pipelineStatus, [node]: 'complete' as const } : prev.pipelineStatus
          }));
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
      setState(prev => ({
        ...prev,
        isDeploying: true,
        activeAgent: 'parser',
        directiveLogs: [...prev.directiveLogs, `[User] ${directive}`],
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
