"use client";

import { useState, useEffect, useRef, useCallback } from 'react';

// Define the strict schemas your parser is supposed to be sending
export interface SwarmState {
  isConnected: boolean;
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
        if (payload.type === 'human_checkpoint') {
          setState(prev => ({
            ...prev,
            pendingAction: payload.trade_details
          }));
        }

        // Handle raw system logs
        if (payload.type === 'log') {
          setState(prev => ({
            ...prev,
            directiveLogs: [...prev.directiveLogs, payload.message]
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
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'start_swarm', payload: directive }));
    } else {
      console.error("Cannot deploy: Nexus is offline.");
    }
  }, []);

  const resolveCheckpoint = useCallback((approved: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && state.pendingAction) {
      wsRef.current.send(JSON.stringify({ 
        action: 'resolve_checkpoint', 
        decision: approved ? 'APPROVE' : 'REJECT' 
      }));
      // Clear the action center once resolved
      setState(prev => ({ ...prev, pendingAction: null }));
    }
  }, [state.pendingAction]);

  return { state, deployDirective, resolveCheckpoint };
}
