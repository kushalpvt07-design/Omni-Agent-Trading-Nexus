"use client";

import React from "react";
import { useSwarmWebSocket } from "@/hooks/useSwarmWebSocket";
import SwarmDirectiveInput from "@/components/SwarmDirectiveInput";
import AssetIntelligence from "@/components/AssetIntelligence";
import MarketPulse from "@/components/MarketPulse";
import SwarmConsensus from "@/components/SwarmConsensus";
import PortfolioLedger from "@/components/PortfolioLedger";
import HumanInTheLoopModal from "@/components/HumanInTheLoopModal";
import { Activity, Zap, Shield } from "lucide-react";

export default function OmniAgentNexus() {
  const { state, deployDirective, resolveCheckpoint } = useSwarmWebSocket(
    "ws://127.0.0.1:8000/api/v1/swarm-stream",
    process.env.NEXT_PUBLIC_NEXUS_API_SECRET
  );

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200 font-sans relative overflow-x-hidden selection:bg-teal-500/30">
      
      {/* ---- Animated Background Layer ---- */}
      <div className="fixed inset-0 pointer-events-none z-0">
        {/* Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a08_1px,transparent_1px),linear-gradient(to_bottom,#0f172a08_1px,transparent_1px)] bg-[size:40px_40px]" />
        {/* Radial gradient glow */}
        <div className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] rounded-full bg-teal-500/[0.03] blur-[120px] orb-1" />
        <div className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] rounded-full bg-cyan-500/[0.03] blur-[100px] orb-2" />
        <div className="absolute top-[40%] right-[30%] w-[300px] h-[300px] rounded-full bg-emerald-500/[0.02] blur-[80px] orb-1" />
        {/* Scan line */}
        <div className="absolute w-full h-[1px] bg-gradient-to-r from-transparent via-teal-400/10 to-transparent" style={{ animation: 'scan-line 8s linear infinite' }} />
      </div>

      {/* ---- Content ---- */}
      <div className="relative z-10 p-4 md:p-6 lg:p-8">

        {/* ========= HEADER ========= */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 pb-5 border-b border-slate-800/40 gap-4 animate-fade-in-up">
          <div className="flex items-center gap-4">
            {/* Logo mark */}
            <div className="relative group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/10 border border-teal-500/30 flex items-center justify-center glow-teal transition-all duration-500 group-hover:glow-teal-strong group-hover:scale-105">
                <Zap className="w-5 h-5 text-teal-400" />
              </div>
              <div className="absolute -inset-1 rounded-xl bg-teal-400/10 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100 font-sans">
                Omni-Agent Trading <span className="text-glow-teal text-teal-400">Nexus</span>
              </h1>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5 tracking-wider">
                Autonomous Swarm Financial Execution Engine & Consensus Pipeline
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Security badge */}
            <div className="flex items-center gap-1.5 text-[10px] font-mono px-2.5 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800/60 text-slate-500">
              <Shield className="w-3 h-3" />
              <span>PAPER MODE</span>
            </div>
            
            {/* Connection indicator */}
            <div className={`flex items-center gap-2 text-xs font-mono px-3.5 py-2 rounded-xl transition-all duration-500 ${
              state.isConnected 
                ? "bg-teal-950/30 border border-teal-500/25 glow-teal" 
                : "bg-red-950/20 border border-red-500/20"
            }`}>
              <div className="relative">
                <Activity className={`w-3.5 h-3.5 ${state.isConnected ? "text-teal-400" : "text-red-500"}`} />
                {state.isConnected && (
                  <div className="absolute inset-0 animate-ping">
                    <Activity className="w-3.5 h-3.5 text-teal-400 opacity-30" />
                  </div>
                )}
              </div>
              <span className={`font-semibold tracking-wide ${state.isConnected ? "text-teal-400 text-glow-teal" : "text-red-400"}`}>
                {state.isConnected ? "SYSTEM LIVE" : "DISCONNECTED"}
              </span>
            </div>
          </div>
        </header>

        {/* ========= MAIN GRID ========= */}
        <main className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-6 mb-6">
          
          {/* Left Column: Command & Pipeline */}
          <div className="lg:col-span-5 flex flex-col gap-5 lg:gap-6" style={{ animationDelay: '0.1s' }}>
            <div className="h-[460px] animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
              <SwarmDirectiveInput 
                logs={state.directiveLogs} 
                isDeploying={state.isDeploying} 
                onSendDirective={deployDirective} 
              />
            </div>
            <div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              <PortfolioLedger portfolioData={state.portfolioData} />
            </div>
          </div>

          {/* Right Column: Asset Telemetry & Consensus */}
          <div className="lg:col-span-7 flex flex-col gap-5 lg:gap-6">
            <div className="h-[300px] animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
              <AssetIntelligence assetData={state.assetData} />
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 lg:gap-6">
              <div className="animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
                <SwarmConsensus sentimentData={state.sentimentData} />
              </div>
              <div className="animate-fade-in-up" style={{ animationDelay: '0.35s' }}>
                <MarketPulse sentimentData={state.sentimentData} />
              </div>
            </div>
          </div>

        </main>

        {/* Footer bar */}
        <footer className="flex items-center justify-between py-3 border-t border-slate-800/30 text-[10px] font-mono text-slate-600 animate-fade-in" style={{ animationDelay: '0.5s' }}>
          <span>OMNI-NEXUS v1.0 • Multi-Agent Swarm Architecture</span>
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-500/50 animate-pulse" />
            All systems nominal
          </span>
        </footer>
      </div>

      <HumanInTheLoopModal
        checkpoint={state.pendingCheckpoint}
        onResolve={resolveCheckpoint}
      />
    </div>
  );
}
