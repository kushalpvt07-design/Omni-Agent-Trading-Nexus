"use client";

import React from "react";
import { Newspaper, Zap } from "lucide-react";

export default function MarketPulse({ sentimentData }: { sentimentData: any }) {
  const headlines =
    sentimentData?.top_headlines ||
    sentimentData?.news_headlines ||
    sentimentData?.headlines ||
    [];

  return (
    <div className="w-full h-[310px] rounded-2xl bento-card p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center">
            <Newspaper className="w-3.5 h-3.5 text-teal-600" />
          </div>
          <div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-900 uppercase">
              Market Pulse
            </h2>
            <p className="text-[10px] font-mono text-slate-500">
              Live News Feed &amp; Summaries
            </p>
          </div>
        </div>
        {headlines.length > 0 && (
          <span className="text-[10px] font-mono font-semibold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-md border border-teal-200 flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {headlines.length} items
          </span>
        )}
      </div>

      {/* Parsed Headlines Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2.5 pr-1 min-h-0">
        {!headlines || headlines.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 bg-slate-50/70 rounded-xl border border-dashed border-slate-200">
            <Newspaper className="w-6 h-6 text-slate-400" />
            <span className="text-xs text-slate-500 font-mono">
              Awaiting live market news...
            </span>
          </div>
        ) : (
          headlines.map((headline: any, i: number) => {
            const rawText =
              typeof headline === "string"
                ? headline
                : headline.title || headline.text || "Market Update";

            let cleanTitle = rawText;
            let cleanSummary = "";
            if (rawText.includes(" | Summary:")) {
              const parts = rawText.split(" | Summary:");
              cleanTitle = parts[0].replace(/^Title:\s*/i, "").trim();
              cleanSummary = (parts[1] || "").trim();
            } else {
              cleanTitle = rawText.replace(/^Title:\s*/i, "").trim();
            }

            return (
              <div
                key={i}
                className="flex flex-col gap-1 p-3 rounded-xl border border-slate-200/80 bg-slate-50/70 hover:bg-white hover:border-teal-300 transition-all animate-fade-in-up"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-teal-500 mt-1.5 shrink-0" />
                    <p className="text-xs font-semibold text-slate-900 font-sans leading-snug line-clamp-2">
                      {cleanTitle}
                    </p>
                  </div>
                  <span className="text-[9px] font-mono font-semibold text-teal-700 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded uppercase shrink-0">
                    Live
                  </span>
                </div>
                {cleanSummary && (
                  <p className="text-[11px] text-slate-500 font-sans leading-relaxed pl-4 line-clamp-2">
                    {cleanSummary}
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
