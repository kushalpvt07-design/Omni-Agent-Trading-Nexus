"use client";

import React, { useRef, useEffect } from "react";
import { GitCommit, Layers, CheckCircle2, AlertTriangle } from "lucide-react";
import { LogMessage } from "@/hooks/useSwarmWebSocket";

export default function NexusPipelineLog({ logs }: { logs: LogMessage[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const pipelineLogs = logs.filter(l => l.type === "status" || l.type === "checkpoint");

  return (
    <div className="w-full rounded-2xl glass-card gradient-border p-5 group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15">
            <Layers className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Nexus Pipeline Log
          </h2>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${pipelineLogs.length > 0 ? 'bg-teal-400 animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-[9px] font-mono text-slate-500">
            {pipelineLogs.length > 0 ? `${pipelineLogs.length} events` : 'Idle'}
          </span>
        </div>
      </div>

      {/* Log Stream */}
      <div className="h-[130px] bg-[#020406]/60 rounded-xl border border-slate-800/30 p-3 overflow-y-auto font-mono text-[10px] space-y-2 custom-scrollbar relative">
        {/* Gradient left accent line */}
        <div className="absolute left-0 top-0 bottom-0 w-[2px] rounded-full bg-gradient-to-b from-teal-500/40 via-teal-500/10 to-transparent" />

        {pipelineLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-slate-600 italic text-[11px] flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
              No automated sub-routines running
            </p>
          </div>
        ) : (
          pipelineLogs.map((log, index) => (
            <div 
              key={index} 
              className="flex items-start gap-2.5 pl-2 animate-slide-in-right" 
              style={{ animationDelay: `${Math.min(index * 0.05, 0.25)}s` }}
            >
              <span className="text-slate-700 shrink-0 text-[9px] mt-0.5 w-[52px]">
                {log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
              </span>
              {log.type === "checkpoint" ? (
                <AlertTriangle className="w-3 h-3 text-purple-400 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-3 h-3 text-teal-500/60 shrink-0 mt-0.5" />
              )}
              <span className={`leading-relaxed ${log.type === "checkpoint" ? "text-purple-300 font-semibold" : "text-slate-400"}`}>
                {log.content}
              </span>
            </div>
          ))
        )}
        <div ref={scrollRef} />
      </div>
    </div>
  );
}
