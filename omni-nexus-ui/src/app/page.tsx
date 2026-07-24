"use client";

import React, { useState } from 'react';
import { useSwarmWebSocket } from '@/hooks/useSwarmWebSocket';
import SwarmDirectiveInput from '@/components/SwarmDirectiveInput';
import AssetIntelligence from '@/components/AssetIntelligence';
import { SwarmChat } from '@/components/SwarmChat'; // Make sure you actually import it

export default function OmniAgentNexus() {
  const [inputDirective, setInputDirective] = useState("e.g. Let's scoop up 25 shares of AAPL");
  const { state, deployDirective, resolveCheckpoint } = useSwarmWebSocket('ws://127.0.0.1:8000/api/v1/swarm-stream');

  const getStepIcon = (status: 'pending' | 'active' | 'complete' | 'error') => {
    switch (status) {
      case 'active': return { icon: '⚙', color: 'text-sky-400' };
      case 'complete': return { icon: '✓', color: 'text-emerald-500' };
      case 'error': return { icon: '✕', color: 'text-red-500' };
      default: return { icon: '○', color: 'text-slate-600' };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6 font-sans">
      <header className="flex justify-between items-center mb-6 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-full border-4 border-slate-500 bg-slate-800"></div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-wider">OMNI-AGENT TRADING NEXUS</h1>
          <span className={`text-xs px-2 py-0.5 rounded ${state.isConnected ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'}`}>
            {state.isConnected ? 'Live Nexus Connected' : 'Nexus Disconnected'}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-[400px]">
          <SwarmDirectiveInput 
            logs={state.directiveLogs}
            isDeploying={state.isDeploying}
            onSendDirective={deployDirective}
          />
        </div>

        <div className="h-[400px]">
          <AssetIntelligence assetData={state.assetData} />
        </div>
      </div>
      
      {/* Properly integrated SwarmChat sharing the single WebSocket connection */}
      <SwarmChat 
        deployDirective={deployDirective} 
        isConnected={state.isConnected} 
        externalLogs={state.directiveLogs} 
      />
    </div>
  );
}
