"use client";

import React, { useRef, useEffect } from "react";
import { GitCommit, Layers } from "lucide-react";
import { LogMessage } from "@/hooks/useSwarmWebSocket";

export default function NexusPipelineLog({ logs }: { logs: LogMessage[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const pipelineLogs = logs.filter(l => l.type === "status" || l.type === "checkpoint");

  return (
    <div className="w-full rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80 mb-3">
        <Layers className="w-4 h-4 text-teal-400" />
        <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
          Nexus Log: Active Swarm Pipeline
        </h2>
      </div>

      <div className="h-[120px] bg-[#05080F] rounded-xl border border-slate-800/60 p-3 overflow-y-auto font-mono text-[11px] space-y-2 border-l-2 border-l-teal-500/50">
        {pipelineLogs.length === 0 ? (
          <p className="text-slate-600 italic">No automated sub-routines running.</p>
        ) : (
          pipelineLogs.map((log) => (
            <div key={log.id} className="flex items-start gap-3">
              <span className="text-slate-600 shrink-0">[{log.timestamp}]</span>
              <GitCommit className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
              <span className={log.type === "checkpoint" ? "text-purple-300 font-bold" : "text-slate-300"}>
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
