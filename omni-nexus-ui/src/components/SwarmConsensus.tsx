"use client";

import React from "react";
import { Target, Activity, TrendingUp, TrendingDown, Scale } from "lucide-react";

function formatHighlightedReasoning(text: string) {
  if (!text) return null;
  // Highlight prices ($323.38), percentages (22.65%), actions (BUY, SELL, HOLD, REJECT), and RSI/SMA tokens
  const parts = text.split(
    /(\$[0-9,.]+|₹[0-9,.]+|[0-9]+\.[0-9]+%|\bBUY\b|\bSELL\b|\bHOLD\b|\bREJECT\b|\bRSI(?:\(14\))?\b|\bSMA\b)/g
  );
  return parts.map((part, i) => {
    if (/^(\$|₹)[0-9,.]+$/.test(part) || /^[0-9]+\.[0-9]+%$/.test(part)) {
      return (
        <span
          key={i}
          className="font-mono font-semibold text-slate-900 bg-white px-1.5 py-0.5 rounded border border-slate-200 mx-0.5"
        >
          {part}
        </span>
      );
    }
    if (part === "BUY") {
      return (
        <span
          key={i}
          className="font-mono font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 mx-0.5"
        >
          {part}
        </span>
      );
    }
    if (part === "SELL" || part === "REJECT") {
      return (
        <span
          key={i}
          className="font-mono font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200 mx-0.5"
        >
          {part}
        </span>
      );
    }
    if (part === "HOLD") {
      return (
        <span
          key={i}
          className="font-mono font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 mx-0.5"
        >
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function SwarmConsensus({
  sentimentData,
  assetData,
}: {
  sentimentData: any;
  assetData?: any;
}) {
  if (!sentimentData) {
    return (
      <div className="w-full h-[310px] rounded-2xl bento-card p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center">
              <Target className="w-3.5 h-3.5 text-teal-600" />
            </div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-800 uppercase">
              Swarm Consensus &amp; Synthesis
            </h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-2 bg-slate-50/70 rounded-xl border border-dashed border-slate-200">
          <Target className="w-6 h-6 text-slate-400" />
          <span className="text-slate-500 font-mono text-xs">
            Awaiting Orchestrator 65/35 synthesis...
          </span>
        </div>
      </div>
    );
  }

  const label = sentimentData.sentiment_label || "NEUTRAL";
  const rawScore = sentimentData.sentiment_score ?? 0.5;
  const isBullish = rawScore > 0.6;
  const isBearish = rawScore < 0.4;
  const scorePercent = Math.round(rawScore * 100);
  const reasoning =
    sentimentData.reasoning ||
    "Orchestrator synthesis in progress. Evaluating quantitative price action against news polarity.";

  const price = Number(assetData?.current_price ?? 0);
  const sma = Number(assetData?.thirty_day_sma ?? price);
  const quantBullish = price >= sma;

  const badgeStyle = isBullish
    ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : isBearish
    ? "text-rose-700 bg-rose-50 border-rose-200"
    : "text-amber-700 bg-amber-50 border-amber-200";

  return (
    <div className="w-full h-[310px] rounded-2xl bento-card p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center">
            <Target className="w-3.5 h-3.5 text-teal-600" />
          </div>
          <div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-900 uppercase">
              Swarm Consensus
            </h2>
            <p className="text-[10px] font-mono text-slate-500">
              65% Quantitative Technicals • 35% News Polarity
            </p>
          </div>
        </div>

        <div
          className={`flex items-center gap-1.5 text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg border ${badgeStyle}`}
        >
          {isBullish ? (
            <TrendingUp className="w-3.5 h-3.5" />
          ) : isBearish ? (
            <TrendingDown className="w-3.5 h-3.5" />
          ) : (
            <Activity className="w-3.5 h-3.5" />
          )}
          <span>
            {scorePercent}% {label}
          </span>
        </div>
      </div>

      {/* 65% Quant / 35% Sentiment Tug-of-War Weight Bar */}
      <div className="mb-3 p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
        <div className="flex items-center justify-between text-[10px] font-mono mb-1.5">
          <span className="font-semibold text-slate-700 flex items-center gap-1">
            <Scale className="w-3 h-3 text-teal-600" />
            Quant Technicals (65% Wt):{" "}
            <strong className={quantBullish ? "text-emerald-600" : "text-rose-600"}>
              {quantBullish ? "Above SMA" : "Below SMA"}
            </strong>
          </span>
          <span className="font-semibold text-slate-700">
            News Bias (35% Wt):{" "}
            <strong
              className={
                isBullish
                  ? "text-emerald-600"
                  : isBearish
                  ? "text-rose-600"
                  : "text-amber-600"
              }
            >
              {label}
            </strong>
          </span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden flex">
          <div
            className={`h-full transition-all duration-500 ${
              quantBullish ? "bg-teal-600" : "bg-indigo-600"
            }`}
            style={{ width: "65%" }}
          />
          <div
            className={`h-full transition-all duration-500 ${
              isBullish
                ? "bg-emerald-500"
                : isBearish
                ? "bg-rose-500"
                : "bg-amber-500"
            }`}
            style={{ width: "35%" }}
          />
        </div>
      </div>

      {/* Full-Width Scannable Orchestrator Synthesis */}
      <div className="flex-1 min-h-0 flex flex-col">
        <span className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-teal-600" />
          Orchestrator Decision Reasoning
        </span>
        <div className="flex-1 text-xs text-slate-700 font-sans leading-relaxed bg-[#F8FAFC] p-3.5 rounded-xl border border-slate-200/90 overflow-y-auto custom-scrollbar">
          {formatHighlightedReasoning(reasoning)}
        </div>
      </div>
    </div>
  );
}
