"use client";

import React, { useState, useEffect, useRef } from "react";
import { Terminal, Send, Loader2, Bot, User } from "lucide-react";
import { LogMessage } from "@/hooks/useSwarmWebSocket";

interface Props {
  logs: LogMessage[];
  isDeploying: boolean;
  onSendDirective: (directive: string) => void;
}

export default function CommandTerminal({ logs, isDeploying, onSendDirective }: Props) {
  const [directive, setDirective] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!directive.trim() || isDeploying) return;
    onSendDirective(directive.trim());
    setDirective("");
  };

  const agentMessages = logs.filter(
    (l) => l.type === "user" || (l.type === "message" && l.role)
  );

  const formatMarkdown = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={idx} className="text-teal-300 font-bold">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="w-full h-[380px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/90 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80 mb-3">
        <Terminal className="w-4 h-4 text-teal-400" />
        <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
          Omni-Agent: Command Terminal
        </h2>
      </div>

      <div className="flex-1 w-full bg-[#05080F] rounded-xl border border-slate-800/60 p-3 overflow-y-auto space-y-4 font-mono text-xs custom-scrollbar">
        {agentMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2">
            <Bot className="w-6 h-6 opacity-40" />
            <p className="italic">Terminal idle. Awaiting tactical directive.</p>
          </div>
        ) : (
          agentMessages.map((msg, index) => (
            <div key={index} className={`flex gap-2.5 ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
              {msg.type !== "user" && (
                <div className="w-6 h-6 rounded-md bg-teal-950/50 border border-teal-500/40 flex items-center justify-center text-teal-400 shrink-0">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}
              <div className={`max-w-[85%] rounded-xl p-3 ${msg.type === "user" ? "bg-teal-950/30 border border-teal-500/20 text-teal-100" : "bg-[#0D1420] border border-slate-800 text-slate-300"}`}>
                <div className="text-[10px] text-slate-500 mb-1 flex justify-between gap-4">
                  <span className="font-bold uppercase text-teal-400">{msg.role || "SYSTEM"}</span>
                  <span>{msg.timestamp}</span>
                </div>
                <div className="leading-relaxed whitespace-pre-wrap">{formatMarkdown(msg.content)}</div>
              </div>
              {msg.type === "user" && (
                <div className="w-6 h-6 rounded-md bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          disabled={isDeploying}
          placeholder="Command input here..."
          className="flex-1 bg-[#05080F] border border-slate-800 focus:border-teal-500/50 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 font-mono outline-none transition-all"
        />
        <button
          type="submit"
          disabled={isDeploying || !directive.trim()}
          className="px-4 py-2 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/50 text-teal-400 font-mono text-xs font-bold tracking-wider uppercase transition-all shadow-[0_0_15px_rgba(20,184,166,0.1)] disabled:opacity-40 flex items-center gap-2 cursor-pointer"
        >
          {isDeploying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          Deploy
        </button>
      </form>
    </div>
  );
}
