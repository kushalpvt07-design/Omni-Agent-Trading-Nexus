"use client";

import React from "react";
import { Target, Activity } from "lucide-react";

export default function SwarmConsensus({ sentimentData }: { sentimentData: any }) {
  if (!sentimentData) {
    return (
      <div className="w-full h-[240px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md items-center justify-center">
        <span className="text-slate-500 font-mono animate-pulse">Awaiting Swarm Consensus Data...</span>
      </div>
    );
  }

  const label = sentimentData.sentiment_label || "NEUTRAL";
  const rawScore = sentimentData.sentiment_score || 0.5;
  const isBullish = rawScore > 0.5;
  const rotation = Math.max(0, Math.min((rawScore * 180), 180));
  const reasoning = sentimentData.reasoning || "No synthetic reasoning generated. Run a prompt to initiate swarm analysis.";

  return (
    <div className="w-full h-[240px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-teal-400" />
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Swarm Consensus: Analysis
          </h2>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Left Side: Gauge & Vectors */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center border-r border-slate-800/60 pr-2 h-full">
          <div className="relative flex flex-col items-center mt-2">
            <div className="relative w-24 h-12 overflow-hidden">
              <div className="absolute w-24 h-24 rounded-full border-[10px] border-slate-800 border-b-transparent border-r-transparent rotate-45" />
              <div 
                className="absolute w-24 h-24 rounded-full border-[10px] border-teal-500 border-b-transparent border-r-transparent transition-transform duration-1000 ease-out origin-center"
                style={{ transform: `rotate(${rotation - 135}deg)` }} 
              />
            </div>
            <div className="absolute -bottom-2 text-center">
               <p className={`text-sm font-bold font-mono tracking-wide ${isBullish ? 'text-teal-400' : 'text-rose-400'}`}>
                  {label}
               </p>
            </div>
          </div>

          <div className="flex flex-col gap-1.5 mt-6 w-full items-center">
            <div className="flex flex-wrap justify-center gap-1">
              {["Volume", "Momentum", "News Flow", "Macro"].map(tag => (
                <span key={tag} className="text-[9px] font-mono text-slate-300 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Side: Agent Reasoning Text */}
        <div className="lg:col-span-7 flex flex-col h-full justify-start space-y-2 pl-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-teal-400" /> Orchestrator Synthesis
          </span>
          <div className="flex-1 text-xs text-slate-300 font-sans leading-relaxed bg-[#05080F] p-3 rounded-lg border border-slate-800/80 overflow-y-auto custom-scrollbar">
            {reasoning}
          </div>
        </div>
      </div>
    </div>
  );
}
