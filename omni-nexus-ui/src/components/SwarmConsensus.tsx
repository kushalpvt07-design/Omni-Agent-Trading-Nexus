"use client";

import React from "react";
import { Target, Activity, TrendingUp, TrendingDown } from "lucide-react";

export default function SwarmConsensus({ sentimentData }: { sentimentData: any }) {
  if (!sentimentData) {
    return (
      <div className="w-full h-[260px] rounded-2xl glass-card gradient-border p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <Target className="w-3.5 h-3.5 text-teal-400" />
            </div>
            <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-300 uppercase">
              Swarm Consensus
            </h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <div className="relative">
            <div className="w-12 h-12 rounded-full border-2 border-teal-500/15 flex items-center justify-center animate-float">
              <Target className="w-5 h-5 text-teal-500/30" />
            </div>
            <div className="absolute inset-0 rounded-full bg-teal-400/5 blur-xl animate-glow-pulse" />
          </div>
          <span className="text-slate-500 font-mono text-xs">Awaiting Swarm Consensus Data...</span>
        </div>
      </div>
    );
  }

  const label = sentimentData.sentiment_label || "NEUTRAL";
  const rawScore = sentimentData.sentiment_score || 0.5;
  const isBullish = rawScore > 0.5;
  const scorePercent = Math.round(rawScore * 100);
  const rotation = Math.max(0, Math.min((rawScore * 180), 180));
  const reasoning = sentimentData.reasoning || "No synthetic reasoning generated. Run a prompt to initiate swarm analysis.";

  return (
    <div className="w-full h-[260px] rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15">
            <Target className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Swarm Consensus
          </h2>
        </div>
        {/* Live sentiment badge */}
        <div className={`flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded-lg border ${
          isBullish 
            ? 'text-teal-400 bg-teal-950/20 border-teal-500/20' 
            : 'text-rose-400 bg-rose-950/20 border-rose-500/20'
        }`}>
          {isBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {label}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 items-center min-h-0">
        {/* Left: Gauge */}
        <div className="lg:col-span-5 flex flex-col items-center justify-center border-r border-slate-800/30 pr-2 h-full">
          {/* Semi-circle Gauge */}
          <div className="relative flex flex-col items-center">
            <div className="relative w-28 h-14 overflow-hidden">
              {/* Background track */}
              <div className="absolute w-28 h-28 rounded-full border-[10px] border-slate-800/60 border-b-transparent border-r-transparent rotate-45" />
              {/* Animated fill */}
              <div 
                className="absolute w-28 h-28 rounded-full border-[10px] border-b-transparent border-r-transparent transition-transform duration-1000 ease-out origin-center animate-gauge-fill"
                style={{ 
                  transform: `rotate(${rotation - 135}deg)`,
                  borderColor: isBullish ? '#2dd4bf' : '#f43f5e',
                  borderBottomColor: 'transparent',
                  borderRightColor: 'transparent',
                  filter: `drop-shadow(0 0 8px ${isBullish ? 'rgba(45,212,191,0.3)' : 'rgba(244,63,94,0.3)'})`
                }} 
              />
            </div>
            {/* Score */}
            <div className="mt-1 text-center">
              <p className={`text-lg font-bold font-mono tracking-wide ${isBullish ? 'text-teal-400 text-glow-teal' : 'text-rose-400'}`}>
                {scorePercent}%
              </p>
              <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">{label}</p>
            </div>
          </div>

          {/* Signal Tags */}
          <div className="flex flex-wrap justify-center gap-1 mt-3">
            {["Volume", "Momentum", "News", "Macro"].map(tag => (
              <span key={tag} className="text-[8px] font-mono text-slate-400 bg-slate-900/60 border border-slate-800/50 px-1.5 py-0.5 rounded-md transition-all duration-300 hover:border-teal-500/20 hover:text-teal-400/80 cursor-default">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Right: Reasoning */}
        <div className="lg:col-span-7 flex flex-col h-full justify-start space-y-1.5 pl-2 min-h-0">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-teal-400" /> Orchestrator Synthesis
          </span>
          <div className="flex-1 text-[11px] text-slate-300/90 font-sans leading-relaxed bg-[#030508]/60 p-3 rounded-xl border border-slate-800/40 overflow-y-auto custom-scrollbar">
            {reasoning}
          </div>
        </div>
      </div>
    </div>
  );
}
