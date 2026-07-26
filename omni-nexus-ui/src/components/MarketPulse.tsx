"use client";

import React from "react";
import { Newspaper } from "lucide-react";

export default function MarketPulse({ sentimentData }: { sentimentData: any }) {
  // Gracefully handle the chaotic array, now explicitly checking for top_headlines
  const headlines = sentimentData?.top_headlines || sentimentData?.news_headlines || sentimentData?.headlines || [];

  return (
    <div className="w-full h-[240px] rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-teal-400" />
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Market Pulse: Headlines
          </h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-3 pr-2">
        {!headlines || headlines.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-xs text-slate-500 font-mono animate-pulse">
            Awaiting market news feed...
          </div>
        ) : (
          headlines.map((headline: any, i: number) => {
            const titleText = typeof headline === 'string' ? headline : headline.title || headline.text || "Unknown Headline";
            return (
              <div key={i} className="flex items-start justify-between gap-3 p-3 rounded-lg border border-slate-800/60 bg-[#05080F]">
                <p className="text-xs text-slate-300 font-sans leading-relaxed break-words whitespace-normal">
                  {titleText}
                </p>
                <span className="text-[9px] font-mono text-teal-400 bg-teal-950/30 border border-teal-900 px-2 py-0.5 rounded uppercase mt-0.5 shrink-0">
                  Scraped
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
