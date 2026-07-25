"use client";

import React from "react";
import { Target, Activity } from "lucide-react";

export default function SwarmConsensus({ sentimentData }: { sentimentData: any }) {
  const label = sentimentData?.sentiment_label || "NEUTRAL";
  const rawScore = sentimentData?.sentiment_score || 0.5;
  const isBullish = rawScore > 0.5;
  
  const rotation = Math.max(0, Math.min((rawScore * 180), 180));

  return (
    <div className="w-full h-[240px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-teal-400" />
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Swarm Consensus: Bias
          </h2>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center gap-8">
        <div className="relative flex flex-col items-center">
          <div className="relative w-32 h-16 overflow-hidden">
            <div className="absolute w-32 h-32 rounded-full border-[12px] border-slate-800 border-b-transparent border-r-transparent rotate-45" />
            <div 
              className="absolute w-32 h-32 rounded-full border-[12px] border-teal-500 border-b-transparent border-r-transparent transition-transform duration-1000 ease-out origin-center"
              style={{ transform: `rotate(${rotation - 135}deg)` }} 
            />
          </div>
          <div className="absolute bottom-0 text-center">
             <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Bias</span>
             <p className={`text-lg font-bold font-mono tracking-wide ${isBullish ? 'text-teal-400' : 'text-rose-400'}`}>
                {label}
             </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1 uppercase">
            <Activity className="w-3 h-3 text-teal-400" /> Data Vectors
          </span>
          <div className="flex flex-wrap gap-1.5 max-w-[120px]">
            {["Volume", "Momentum", "News Flow", "Macro"].map(tag => (
              <span key={tag} className="text-[9px] font-mono text-slate-300 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
