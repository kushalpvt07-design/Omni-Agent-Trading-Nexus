"use client";

import React from "react";
import { Newspaper } from "lucide-react";

export default function MarketPulse({ sentimentData }: { sentimentData: any }) {
  const headlines = sentimentData?.top_headlines || [
    "Awaiting tactical directive formulation...",
    "Swarm intelligence modules offline."
  ];

  return (
    <div className="w-full h-[240px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80 mb-3">
        <Newspaper className="w-4 h-4 text-teal-400" />
        <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
          Market Pulse: Headlines
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 font-mono pr-2">
        {headlines.map((item: string, idx: number) => (
          <div key={idx} className="p-2.5 rounded-lg bg-[#05080F] border border-slate-800/50 flex justify-between gap-3 items-center">
            <p className="text-[11px] text-slate-300 truncate">{item}</p>
            <span className="text-[9px] font-bold text-teal-400 bg-teal-950/50 px-1.5 py-0.5 rounded border border-teal-500/20 shrink-0">
              Scraped
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
