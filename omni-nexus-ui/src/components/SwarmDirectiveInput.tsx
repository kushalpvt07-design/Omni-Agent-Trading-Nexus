"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Terminal,
  Loader2,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
} from "lucide-react";
import { LogMessage } from "@/hooks/useSwarmWebSocket";

interface Props {
  logs: LogMessage[];
  isDeploying: boolean;
  onSendDirective: (directive: string) => void;
}

const QUICK_DEMO_CHIPS = [
  { label: "⚡ Buy 10 AAPL if vol < 25%", prompt: "Buy 10 shares of AAPL if volatility risk < 25%" },
  { label: "🇮🇳 Buy 20 TCS.NS on NSE", prompt: "Buy 20 shares of TCS on NSE" },
  { label: "₿ Buy 0.25 BTC/USD", prompt: "Buy 0.25 BTC/USD" },
  { label: "📉 Sell 50% of GOOGL", prompt: "Sell 50% of my GOOGL position" },
];

export default function SwarmDirectiveInput({
  logs,
  isDeploying,
  onSendDirective,
}: Props) {
  const [directive, setDirective] = useState("");
  const [showLogs, setShowLogs] = useState(true);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleDeploy = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleaned = directive.trim();
    if (!cleaned || isDeploying) return;
    onSendDirective(cleaned);
    setDirective("");
  };

  const handleChipClick = (promptText: string) => {
    if (isDeploying) return;
    setDirective(promptText);
    onSendDirective(promptText);
  };

  return (
    <div className="w-full flex flex-col rounded-2xl bento-card p-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center">
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
          </div>
          <div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-800 uppercase">
              Swarm Command Center
            </h2>
            <p className="text-[10px] font-mono text-slate-500">
              Natural-Language Directive Input &amp; Quick Scenarios
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span className="font-semibold">Injection-Hardened</span>
        </div>
      </div>

      {/* Spotlight Command Bar */}
      <form onSubmit={handleDeploy} className="p-1 rounded-2xl ai-command-ring mb-3">
        <div className="flex gap-2 bg-white rounded-xl p-1.5 border border-slate-200/80 shadow-xs">
          <input
            type="text"
            value={directive}
            onChange={(e) => setDirective(e.target.value)}
            disabled={isDeploying}
            placeholder='Try: "Buy 15 shares of AAPL if volatility < 25%"'
            className="flex-1 bg-transparent px-3 py-2 text-xs md:text-sm text-slate-900 placeholder-slate-400 font-mono outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isDeploying || !directive.trim()}
            className={`px-4 py-2 rounded-lg font-mono text-xs font-bold tracking-wider uppercase transition-all flex items-center gap-2 shrink-0 cursor-pointer ${
              isDeploying
                ? "bg-teal-100 text-teal-800 cursor-not-allowed"
                : "bg-teal-600 hover:bg-teal-700 text-white shadow-xs active:scale-[0.98]"
            } disabled:opacity-40`}
          >
            {isDeploying ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Running</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Deploy</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* One-Click Demo Chips */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3.5">
        <span className="text-[10px] font-mono text-slate-400 mr-1">
          Quick Demo:
        </span>
        {QUICK_DEMO_CHIPS.map((chip) => (
          <button
            key={chip.label}
            type="button"
            disabled={isDeploying}
            onClick={() => handleChipClick(chip.prompt)}
            className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full bg-slate-100 hover:bg-teal-50 text-slate-700 hover:text-teal-700 border border-slate-200 hover:border-teal-300 transition-all cursor-pointer disabled:opacity-40"
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Collapsible Telemetry Log Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <Terminal className="w-3 h-3 text-slate-400" />
          Live Execution Stream ({logs.length})
        </span>
        <button
          type="button"
          onClick={() => setShowLogs(!showLogs)}
          className="text-[10px] font-mono text-slate-500 hover:text-slate-800 flex items-center gap-1 cursor-pointer"
        >
          {showLogs ? (
            <>
              Hide <ChevronUp className="w-3 h-3" />
            </>
          ) : (
            <>
              Expand <ChevronDown className="w-3 h-3" />
            </>
          )}
        </button>
      </div>

      {/* Light-Mode Structured Telemetry Stream */}
      {showLogs && (
        <div className="h-[195px] w-full bg-slate-50/90 rounded-xl border border-slate-200/90 p-3.5 font-mono text-xs overflow-y-auto space-y-2 custom-scrollbar">
          {logs.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-400 text-[11px]">
              Click any Demo Chip above or type a trade command to launch the 6-agent swarm.
            </div>
          ) : (
            logs.map((log, index) => (
              <div
                key={index}
                className="leading-relaxed text-[11px] bg-white p-2 rounded-lg border border-slate-200/70 shadow-2xs animate-fade-in-up"
              >
                <span className="text-slate-400 mr-2 text-[9px]">
                  {log.timestamp
                    ? new Date(log.timestamp).toLocaleTimeString()
                    : ""}
                </span>
                {log.type === "user" && (
                  <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200 font-bold text-[9px] mr-1.5">
                    USER
                  </span>
                )}
                {log.type === "status" && (
                  <span className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-semibold text-[9px] mr-1.5">
                    PHASE
                  </span>
                )}
                {log.type === "checkpoint" && (
                  <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-bold text-[9px] mr-1.5">
                    HITL GATE
                  </span>
                )}
                {log.type === "message" && log.role !== "USER" && (
                  <span className="px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200 font-bold text-[9px] mr-1.5">
                    {log.role}
                  </span>
                )}
                <span className="text-slate-700">{log.content}</span>
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>
      )}
    </div>
  );
}
