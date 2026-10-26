"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSwarmWebSocket } from "@/hooks/useSwarmWebSocket";
import {
  isAuthenticated,
  isTokenExpired,
  getToken,
  getUser,
  clearAuth,
  AuthUser,
} from "@/lib/auth";
import { AgentNodeId, AgentStepTelemetry } from "@/types/swarm";
import SwarmDirectiveInput from "@/components/SwarmDirectiveInput";
import AssetIntelligence from "@/components/AssetIntelligence";
import MarketPulse from "@/components/MarketPulse";
import SwarmConsensus from "@/components/SwarmConsensus";
import PortfolioLedger from "@/components/PortfolioLedger";
import HumanInTheLoopModal from "@/components/HumanInTheLoopModal";
import {
  Activity,
  Zap,
  Shield,
  LogOut,
  User,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Cpu,
  X,
  Terminal,
  ChevronRight,
  GitBranch,
} from "lucide-react";

export default function OmniAgentNexus() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [inspectedAgent, setInspectedAgent] = useState<AgentNodeId | null>(null);

  useEffect(() => {
    setMounted(true);
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setToken(getToken());
    setUser(getUser());

    const expiryCheck = setInterval(() => {
      if (isTokenExpired()) {
        clearAuth();
        router.replace("/login");
      }
    }, 60_000);

    return () => clearInterval(expiryCheck);
  }, [router]);

  const { state, deployDirective, resolveCheckpoint } = useSwarmWebSocket(
    "ws://localhost:8000/api/v1/swarm-stream",
    token || undefined
  );

  const handleLogout = () => {
    clearAuth();
    router.replace("/login");
  };

  if (!mounted || !token || !user) {
    return (
      <div className="min-h-screen porcelain-blueprint flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-teal-600/30 border-t-teal-600 rounded-full animate-spin" />
      </div>
    );
  }

  // Dynamic Ambient Aura based on active swarm state
  const rawScore = state.sentimentData?.sentiment_score ?? 0.5;
  const isCheckpoint = !!state.pendingCheckpoint;
  const auraColor = isCheckpoint
    ? "from-amber-400/20 via-orange-300/10 to-transparent"
    : rawScore > 0.6
    ? "from-emerald-400/20 via-teal-300/10 to-transparent"
    : rawScore < 0.4
    ? "from-rose-400/20 via-pink-300/10 to-transparent"
    : "from-teal-400/15 via-indigo-300/10 to-transparent";

  const renderNodePill = (step: AgentStepTelemetry) => {
    const isRunning = step.status === "running";
    const isDone = step.status === "completed";
    const isError = step.status === "error";

    return (
      <button
        key={step.id}
        onClick={() => setInspectedAgent(step.id)}
        className={`group relative flex items-center gap-2.5 px-3.5 py-2 rounded-xl border text-left transition-all duration-200 cursor-pointer ${
          isRunning
            ? "bg-teal-50/90 border-teal-500 shadow-sm animate-pulse-ring"
            : isDone
            ? "bg-white border-emerald-500/40 hover:border-emerald-500 shadow-xs"
            : isError
            ? "bg-rose-50 border-rose-400"
            : "bg-slate-50/80 border-slate-200/90 hover:bg-white hover:border-slate-300"
        }`}
        title="Click to inspect raw agent telemetry"
      >
        <div className="shrink-0">
          {isRunning ? (
            <Loader2 className="w-4 h-4 text-teal-600 animate-spin" />
          ) : isDone ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : isError ? (
            <AlertCircle className="w-4 h-4 text-rose-600" />
          ) : (
            <Cpu className="w-4 h-4 text-slate-400 group-hover:text-slate-600" />
          )}
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-bold font-mono text-slate-800 whitespace-nowrap">
              {step.label}
            </span>
            {step.latencyMs !== undefined && (
              <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                {step.latencyMs}ms
              </span>
            )}
          </div>
          <p className="text-[9px] font-mono text-slate-500 truncate">
            {step.shortRole}
          </p>
        </div>
      </button>
    );
  };

  const activeInspected = inspectedAgent ? state.agentSteps[inspectedAgent] : null;

  return (
    <div className="min-h-screen porcelain-blueprint text-slate-900 font-sans relative overflow-x-hidden">
      {/* Dynamic Ambient Aura Mesh */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div
          className={`absolute -top-32 left-1/4 w-[900px] h-[420px] rounded-full bg-gradient-to-br ${auraColor} blur-3xl transition-all duration-1000`}
        />
      </div>

      <div className="relative z-10 max-w-[1600px] mx-auto p-4 md:p-6">
        {/* ========= TOP INSTITUTIONAL HEADER ========= */}
        <header className="bento-card rounded-2xl px-5 py-3.5 mb-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-600 to-emerald-600 flex items-center justify-center shadow-sm shadow-teal-600/20 text-white">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg md:text-xl font-bold tracking-tight text-slate-900">
                  Omni-Agent Trading <span className="text-teal-600">Nexus</span>
                </h1>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
                  AI Quant Workbench
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-mono">
                Autonomous LangGraph Swarm • MCP Tool Servers • Volatility-Targeted Risk Gate
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
              <User className="w-3.5 h-3.5 text-teal-600" />
              <span className="font-semibold">{user.username}</span>
            </div>

            <div className="flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-800">
              <Shield className="w-3.5 h-3.5 text-amber-600" />
              <span className="font-semibold">PAPER TRADING</span>
            </div>

            <div
              className={`flex items-center gap-2 text-[11px] font-mono px-3.5 py-1.5 rounded-xl border ${
                state.isConnected
                  ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                  : "bg-rose-50 border-rose-200 text-rose-800"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  state.isConnected ? "bg-emerald-500 animate-ping" : "bg-rose-500"
                }`}
              />
              <span className="font-bold">
                {state.isConnected ? "SWARM LIVE" : "OFFLINE"}
              </span>
            </div>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-rose-600 hover:border-rose-200 hover:bg-rose-50 transition-all cursor-pointer"
              title="Sign out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {/* ========= INTERACTIVE 6-AGENT NEURAL PIPELINE BAR ========= */}
        <section className="bento-card rounded-2xl px-5 py-3.5 mb-5">
          <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
            <div className="flex items-center gap-2 shrink-0">
              <GitBranch className="w-4 h-4 text-teal-600" />
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-700">
                Live 6-Agent Neural Pipeline
              </span>
              <span className="text-[10px] font-mono text-slate-400 hidden sm:inline">
                (Click any node to inspect raw telemetry)
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 overflow-x-auto py-1">
              {/* 1. Parser */}
              {renderNodePill(state.agentSteps.parser_node)}
              <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />

              {/* 2. Parallel Bracket: Quant MCP + Sentiment MCP */}
              <div className="flex flex-col sm:flex-row items-center gap-1.5 p-1.5 rounded-2xl bg-slate-100/80 border border-dashed border-slate-300">
                <span className="text-[8px] font-mono font-bold uppercase tracking-widest text-teal-700 px-1.5">
                  Parallel Fan-Out
                </span>
                {renderNodePill(state.agentSteps.quant_agent_node)}
                {renderNodePill(state.agentSteps.sentiment_agent_node)}
              </div>

              <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
              {/* 3. Orchestrator */}
              {renderNodePill(state.agentSteps.orchestrator_node)}
              <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
              {/* 4. Risk Desk */}
              {renderNodePill(state.agentSteps.risk_agent_node)}
              <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
              {/* 5. Execution Engine */}
              {renderNodePill(state.agentSteps.execution_agent_node)}
            </div>
          </div>
        </section>

        {/* ========= MAIN 12-COLUMN BENTO WORKSPACE ========= */}
        <main className="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-6">
          {/* Left Column (5 Cols): Smart Command Bar + 3-Tab Portfolio Ledger */}
          <div className="lg:col-span-5 flex flex-col gap-5">
            <SwarmDirectiveInput
              logs={state.directiveLogs}
              isDeploying={state.isDeploying}
              onSendDirective={deployDirective}
            />
            <PortfolioLedger portfolioData={state.portfolioData} token={token} />
          </div>

          {/* Right Column (7 Cols): Asset Intelligence (with SMA overlay) + Consensus + Market Pulse */}
          <div className="lg:col-span-7 flex flex-col gap-5">
            <div className="h-[410px]">
              <AssetIntelligence assetData={state.assetData} />
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
              <div className="xl:col-span-7">
                <SwarmConsensus
                  sentimentData={state.sentimentData}
                  assetData={state.assetData}
                />
              </div>
              <div className="xl:col-span-5">
                <MarketPulse sentimentData={state.sentimentData} />
              </div>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="flex flex-col sm:flex-row items-center justify-between py-3 px-2 border-t border-slate-200/80 text-[11px] font-mono text-slate-500 gap-2">
          <span>OMNI-AGENT TRADING NEXUS • Institutional Daylight Edition</span>
          <span className="flex items-center gap-2 text-emerald-700 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Parallel MCP Fan-Out Active • SQLite WAL Checkpointer Ready
          </span>
        </footer>
      </div>

      {/* ========= SLIDE-OVER AGENT TELEMETRY INSPECTOR DRAWER ========= */}
      {activeInspected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/25 backdrop-blur-xs animate-fade-in-up">
          <div className="w-full max-w-lg bg-white h-full shadow-2xl border-l border-slate-200 p-6 flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-xl bg-teal-50 text-teal-700 border border-teal-200">
                    <Terminal className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 font-mono">
                      {activeInspected.label}
                    </h3>
                    <p className="text-xs text-slate-500 font-mono">
                      Role: {activeInspected.shortRole} • Status:{" "}
                      <span className="uppercase font-semibold text-teal-700">
                        {activeInspected.status}
                      </span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setInspectedAgent(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-5 space-y-4">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <span className="text-xs font-mono text-slate-500">
                    Measured Node Latency
                  </span>
                  <span className="text-sm font-mono font-bold text-emerald-700">
                    {activeInspected.latencyMs !== undefined
                      ? `${activeInspected.latencyMs} ms`
                      : "Pending / Idle"}
                  </span>
                </div>

                <div>
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-500 mb-2">
                    Latest Structured Output / Telemetry
                  </h4>
                  <pre className="p-4 rounded-xl bg-slate-900 text-slate-100 font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {activeInspected.lastOutput ||
                      "No output recorded for this node yet. Deploy a trading directive to inspect live telemetry."}
                  </pre>
                </div>

                <div>
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-500 mb-2">
                    Complete Swarm Event Log
                  </h4>
                  <div className="max-h-64 overflow-y-auto space-y-2 p-3 rounded-xl bg-slate-50 border border-slate-200 font-mono text-xs">
                    {state.directiveLogs.map((l, idx) => (
                      <div key={idx} className="text-slate-700 border-b border-slate-200/60 pb-1.5 last:border-none">
                        <span className="text-teal-700 font-semibold mr-1.5">
                          [{l.role || l.type.toUpperCase()}]
                        </span>
                        {l.content}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => setInspectedAgent(null)}
              className="mt-6 w-full py-2.5 rounded-xl bg-slate-900 text-white font-mono text-xs font-semibold hover:bg-slate-800 cursor-pointer"
            >
              Close Inspector
            </button>
          </div>
        </div>
      )}

      {/* ========= INSTITUTIONAL ORDER TICKET HITL MODAL ========= */}
      <HumanInTheLoopModal
        checkpoint={state.pendingCheckpoint}
        assetData={state.assetData}
        portfolioData={state.portfolioData}
        reasoning={state.sentimentData?.reasoning}
        onResolve={resolveCheckpoint}
      />
    </div>
  );
}
