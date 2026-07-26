"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Terminal, Loader2, CheckCircle2 } from "lucide-react";

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
    <div className="w-full h-full flex flex-col rounded-xl border border-slate-800 bg-[#070A12] p-5 shadow-2xl backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Swarm Directive Input
          </h2>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400/90 bg-emerald-950/30 px-2.5 py-0.5 rounded border border-emerald-800/40">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Hardened Input Enabled</span>
        </div>
      </div>

      {/* Terminal Conversation Output Box */}
      <div className="flex-1 w-full bg-[#030509] rounded-lg border border-slate-800/90 p-4 font-mono text-xs overflow-y-auto space-y-3 shadow-inner">
        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600 italic">
            No directives processed yet. The terminal is on standby.
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="leading-relaxed animate-fade-in">
              <span className="text-slate-600 mr-2">[{log.timestamp}]</span>
              
              {log.type === "user" && (
                <span className="text-cyan-400 font-bold mr-2">&gt; [USER]:</span>
              )}
              {log.type === "status" && (
                <span className="text-amber-400/90 font-semibold mr-2">&gt; [SYSTEM STATUS]:</span>
              )}
              {log.type === "checkpoint" && (
                <span className="text-purple-400 font-bold mr-2">&gt; [CHECKPOINT]:</span>
              )}
              {log.type === "message" && log.role !== "USER" && (
                <span className="text-emerald-400 font-bold mr-2">&gt; [{log.role}]:</span>
              )}

              <span
                className={
                  log.type === "user"
                    ? "text-slate-100 font-medium"
                    : log.type === "status"
                    ? "text-amber-200/80 italic"
                    : log.type === "checkpoint"
                    ? "text-purple-200 font-semibold"
                    : "text-slate-300"
                }
              >
                {log.content}
              </span>
            </div>
          ))
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Input Prompt and Deploy Button */}
      <form onSubmit={handleDeploy} className="mt-4 flex gap-3">
        <input
          type="text"
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          disabled={isDeploying}
          placeholder="e.g. Let's scoop up 25 shares of AAPL if volatility risk < 20%"
          className="flex-1 bg-[#0B0F19] border border-slate-800 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 rounded-lg px-4 py-3 text-sm text-slate-100 placeholder-slate-600 font-mono transition-all outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isDeploying || !directive.trim()}
          className={`px-6 py-3 rounded-lg font-mono text-xs font-bold tracking-wider uppercase transition-all duration-200 flex items-center gap-2 ${
            isDeploying
              ? "bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.15)]"
              : "bg-emerald-600 hover:bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-950/50 active:scale-[0.98] cursor-pointer"
          }`}
        >
          {isDeploying ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>DEPLOYING...</span>
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
