"use client";

import React from "react";
import { useSwarmWebSocket } from "@/hooks/useSwarmWebSocket";
import CommandTerminal from "@/components/CommandTerminal";
import AssetIntelligence from "@/components/AssetIntelligence";
import MarketPulse from "@/components/MarketPulse";
import SwarmConsensus from "@/components/SwarmConsensus";
import NexusPipelineLog from "@/components/NexusPipelineLog";
import HumanInTheLoopModal from "@/components/HumanInTheLoopModal";
import { Activity } from "lucide-react";

export default function OmniAgentNexus() {
  const { state, deployDirective, resolveCheckpoint } = useSwarmWebSocket(
    "ws://127.0.0.1:8000/api/v1/swarm-stream"
  );

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-200 p-4 md:p-6 font-sans relative overflow-x-hidden selection:bg-teal-500/30">
      {/* Background Cyber Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* HEADER */}
      <header className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-slate-800/80 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-5 h-5 rounded-full border-2 border-teal-400 bg-teal-950 flex items-center justify-center animate-pulse">
                <div className="w-2 h-2 rounded-full bg-teal-400" />
              </div>
              <div className="absolute inset-0 rounded-full bg-teal-400/20 blur-md" />
            </div>
            <h1 className="text-xl md:text-2xl font-bold tracking-wider text-slate-100 uppercase font-mono">
              Omni-Agent Trading Nexus
            </h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Autonomous Swarm Financial Execution Engine & Consensus Pipeline
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-[#0D1420] border border-slate-800">
            <Activity className={`w-3.5 h-3.5 ${state.isConnected ? "text-teal-400 animate-pulse" : "text-red-500"}`} />
            <span className={state.isConnected ? "text-teal-400 font-semibold" : "text-red-400 font-semibold"}>
              {state.isConnected ? "SYSTEM LIVE" : "DISCONNECTED"}
            </span>
          </div>
        </div>
      </header>

      {/* 2x2 MAIN GRID */}
      <main className="relative z-10 grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <CommandTerminal 
          logs={state.directiveLogs} 
          isDeploying={state.isDeploying} 
          onSendDirective={deployDirective} 
        />
        <AssetIntelligence assetData={state.assetData} />
        <MarketPulse sentimentData={state.sentimentData} />
        <SwarmConsensus sentimentData={state.sentimentData} />
      </main>

      {/* BOTTOM PANEL */}
      <footer className="relative z-10">
        <NexusPipelineLog logs={state.directiveLogs} />
      </footer>

      {/* HITL OVERLAY MODAL */}
      <HumanInTheLoopModal
        checkpoint={state.pendingCheckpoint}
        onResolve={resolveCheckpoint}
      />
    </div>
  );
}
