"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Terminal, Loader2, CheckCircle2, ChevronRight } from "lucide-react";

import { LogMessage } from "@/hooks/useSwarmWebSocket";

interface Props {
  logs: LogMessage[];
  isDeploying: boolean;
  onSendDirective: (directive: string) => void;
}

export default function SwarmDirectiveInput({ logs, isDeploying, onSendDirective }: Props) {
  const [directive, setDirective] = useState("");
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal to bottom whenever logs update
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleDeploy = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanedDirective = directive.trim();
    if (!cleanedDirective || isDeploying) return;

    onSendDirective(cleanedDirective);
    setDirective(""); // Clear prompt input box
  };

  return (
    <div className="w-full h-full flex flex-col rounded-2xl glass-card gradient-border p-5 group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-emerald-500/15">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Swarm Directive Input
          </h2>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400/80 bg-emerald-950/20 px-2.5 py-1 rounded-lg border border-emerald-500/15 transition-all duration-300 hover:border-emerald-500/30">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>Hardened Input</span>
        </div>
      </div>

      {/* Terminal Output */}
      <div className="flex-1 w-full bg-[#020406]/80 rounded-xl border border-slate-800/40 p-4 font-mono text-xs overflow-y-auto space-y-2.5 shadow-inner custom-scrollbar relative">
        {/* Fake terminal top bar */}
        <div className="flex items-center gap-1.5 mb-3 pb-2 border-b border-slate-800/30">
          <div className="w-2 h-2 rounded-full bg-red-500/40" />
          <div className="w-2 h-2 rounded-full bg-yellow-500/40" />
          <div className="w-2 h-2 rounded-full bg-green-500/40" />
          <span className="text-[9px] text-slate-600 ml-2 font-mono">swarm-terminal</span>
        </div>

        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 italic text-[11px]">
            <span className="cursor-blink">No directives processed yet. The terminal is on standby</span>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="leading-relaxed animate-slide-in-right" style={{ animationDelay: `${Math.min(index * 0.05, 0.3)}s` }}>
              <span className="text-slate-700 mr-2 text-[10px]">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}</span>
              
              {log.type === "user" && (
                <span className="text-cyan-400 font-bold mr-1.5">&gt; <span className="text-cyan-300/60">[USER]</span></span>
              )}
              {log.type === "status" && (
                <span className="text-amber-400/80 font-semibold mr-1.5">
                  <ChevronRight className="w-3 h-3 inline-block -mt-0.5 text-amber-500/60" />
                  <span className="text-amber-300/50">[SYS]</span>
                </span>
              )}
              {log.type === "checkpoint" && (
                <span className="text-purple-400 font-bold mr-1.5">&gt; <span className="text-purple-300/60">[CHECKPOINT]</span></span>
              )}
              {log.type === "message" && log.role !== "USER" && (
                <span className="text-emerald-400 font-bold mr-1.5">
                  <ChevronRight className="w-3 h-3 inline-block -mt-0.5 text-emerald-500/60" />
                  <span className="text-emerald-300/60">[{log.role}]</span>
                </span>
              )}

              <span
                className={
                  log.type === "user"
                    ? "text-slate-100 font-medium"
                    : log.type === "status"
                    ? "text-amber-200/70 italic"
                    : log.type === "checkpoint"
                    ? "text-purple-200 font-semibold"
                    : "text-slate-300/90"
                }
              >
                {log.content}
              </span>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Input + Deploy */}
      <form onSubmit={handleDeploy} className="mt-4 flex gap-2.5">
        <div className="flex-1 relative group/input">
          <input
            type="text"
            value={directive}
            onChange={(e) => setDirective(e.target.value)}
            disabled={isDeploying}
            placeholder='e.g. "Scoop up 25 shares of AAPL if volatility risk < 20%"'
            className="w-full bg-[#080c16] border border-slate-800/60 focus:border-teal-500/40 focus:ring-2 focus:ring-teal-500/10 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-600 font-mono transition-all duration-300 outline-none disabled:opacity-40 disabled:cursor-not-allowed"
          />
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-teal-500/5 to-cyan-500/5 opacity-0 group-focus-within/input:opacity-100 transition-opacity duration-500 pointer-events-none" />
        </div>
        <button
          type="submit"
          disabled={isDeploying || !directive.trim()}
          className={`px-5 py-3 rounded-xl font-mono text-[11px] font-bold tracking-wider uppercase transition-all duration-300 flex items-center gap-2 min-w-[130px] justify-center ${
            isDeploying
              ? "bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 cursor-not-allowed glow-teal"
              : "bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-slate-950 shadow-lg shadow-emerald-950/40 active:scale-[0.97] cursor-pointer hover:shadow-emerald-500/20"
          }`}
        >
          {isDeploying ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
              <span>DEPLOYING</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>DEPLOY</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
