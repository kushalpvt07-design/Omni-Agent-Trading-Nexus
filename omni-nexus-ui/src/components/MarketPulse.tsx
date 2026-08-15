"use client";

import React from "react";
import { Newspaper, ExternalLink, Zap } from "lucide-react";

export default function MarketPulse({ sentimentData }: { sentimentData: any }) {
  // Gracefully handle the chaotic array, now explicitly checking for top_headlines
  const headlines = sentimentData?.top_headlines || sentimentData?.news_headlines || sentimentData?.headlines || [];

  return (
    <div className="w-full h-[260px] rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15">
            <Newspaper className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Market Pulse
          </h2>
        </div>
        {headlines.length > 0 && (
          <span className="text-[9px] font-mono text-teal-400/70 bg-teal-950/20 px-2 py-0.5 rounded-md border border-teal-500/15 flex items-center gap-1">
            <Zap className="w-2.5 h-2.5" />
            {headlines.length} headlines
          </span>
        )}
      </div>

      {/* Headlines Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2 pr-1 min-h-0">
        {!headlines || headlines.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-full border-2 border-teal-500/15 flex items-center justify-center animate-float">
                <Newspaper className="w-4 h-4 text-teal-500/30" />
              </div>
              <div className="absolute inset-0 rounded-full bg-teal-400/5 blur-xl animate-glow-pulse" />
            </div>
            <span className="text-xs text-slate-500 font-mono">Awaiting market news feed...</span>
          </div>
        ) : (
          headlines.map((headline: any, i: number) => {
            const titleText = typeof headline === 'string' ? headline : headline.title || headline.text || "Unknown Headline";
            return (
              <div 
                key={i} 
                className="flex items-start justify-between gap-2.5 p-2.5 rounded-xl border border-slate-800/30 bg-[#030508]/60 transition-all duration-300 hover:border-teal-500/15 hover:bg-[#0a0e17]/60 group/item animate-fade-in-up cursor-default"
                style={{ animationDelay: `${i * 0.08}s` }}
              >
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <div className="w-1 h-1 rounded-full bg-teal-500/50 mt-1.5 shrink-0" />
                  <p className="text-[11px] text-slate-300/90 font-sans leading-relaxed break-words whitespace-normal">
                    {titleText}
                  </p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
                  <span className="text-[8px] font-mono text-teal-400/70 bg-teal-950/25 border border-teal-900/40 px-1.5 py-0.5 rounded-md uppercase">
                    Live
                  </span>
                  <ExternalLink className="w-2.5 h-2.5 text-slate-600 opacity-0 group-hover/item:opacity-100 transition-opacity duration-300" />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
