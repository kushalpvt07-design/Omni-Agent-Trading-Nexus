"use client";

import React, { useState } from "react";
import {
  Newspaper,
  Zap,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  BookOpen,
  TrendingUp,
  TrendingDown,
  Activity,
  X,
} from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";

interface ParsedArticle {
  index: number;
  title: string;
  summary: string;
  source: string;
  url: string;
  isIndirect: boolean;
  tone: "BULLISH" | "BEARISH" | "NEUTRAL";
  matchedKeywords: string[];
}

const BULL_WORDS = new Set([
  "surge", "surges", "surging", "rally", "rallies", "gain", "gains", "rise",
  "rises", "rising", "soar", "soars", "jump", "jumps", "boost", "bullish",
  "upgrade", "upgraded", "beat", "beats", "outperform", "record", "high",
  "breakout", "growth", "profit", "strong", "buy", "positive", "optimistic",
  "recovery", "upbeat", "momentum", "rebound", "advance", "win", "wins",
  "expansion", "deal", "partnership", "dividend",
]);

const BEAR_WORDS = new Set([
  "drop", "drops", "dropped", "fall", "falls", "falling", "decline", "declines",
  "crash", "plunge", "plunges", "loss", "losses", "sink", "bearish",
  "downgrade", "downgraded", "miss", "misses", "underperform", "low", "sell",
  "selloff", "sell-off", "negative", "pessimistic", "risk", "warning", "fear",
  "weak", "slump", "tumble", "concern", "concerns", "worried", "recession",
  "layoff", "layoffs", "cut", "cuts", "debt", "fraud", "scandal", "lawsuit",
  "fail", "fails", "failed", "halt", "halted", "probe", "delay", "delays",
]);

function parseHeadlineItem(rawItem: any, index: number): ParsedArticle {
  const rawText =
    typeof rawItem === "string"
      ? rawItem
      : rawItem?.title || rawItem?.text || "Market Update";

  let cleanTitle = rawText;
  let cleanSummary = "";
  let cleanUrl = typeof rawItem === "object" && rawItem?.url ? String(rawItem.url) : "";

  if (cleanTitle.includes(" | URL:")) {
    const urlParts = cleanTitle.split(" | URL:");
    cleanTitle = urlParts[0];
    cleanUrl = (urlParts[1] || "").trim();
  }

  if (cleanTitle.includes(" | Summary:")) {
    const parts = cleanTitle.split(" | Summary:");
    cleanTitle = parts[0].replace(/^Title:\s*/i, "").trim();
    cleanSummary = (parts[1] || "").trim();
  } else {
    cleanTitle = cleanTitle.replace(/^Title:\s*/i, "").trim();
  }

  if (cleanSummary.includes(" | URL:")) {
    const urlParts = cleanSummary.split(" | URL:");
    cleanSummary = urlParts[0].trim();
    cleanUrl = (urlParts[1] || cleanUrl).trim();
  }

  const isIndirect = cleanTitle.toUpperCase().startsWith("[INDIRECT]");
  cleanTitle = cleanTitle.replace(/^\[(DIRECT|INDIRECT)\]\s*/i, "").trim();

  let source = isIndirect ? "Sector & Macro Wire" : "Financial News Wire";
  const sourceMatch = cleanSummary.match(/^Source:\s*([^.]+)\.\s*(.*)$/i);
  if (sourceMatch) {
    source = sourceMatch[1].trim();
    cleanSummary = sourceMatch[2].trim();
  } else if (cleanTitle.includes(" - ")) {
    const dashParts = cleanTitle.split(" - ");
    const candidateSource = dashParts[dashParts.length - 1].trim();
    if (candidateSource.length > 1 && candidateSource.length <= 28) {
      source = candidateSource;
    }
  }

  const combined = `${cleanTitle} ${cleanSummary}`.toLowerCase();
  const tokens = combined
    .split(/\s+/)
    .map((w) => w.replace(/[^a-z-]/g, ""))
    .filter(Boolean);

  let bullCount = 0;
  let bearCount = 0;
  const matched: string[] = [];

  for (const token of tokens) {
    if (BULL_WORDS.has(token)) {
      bullCount++;
      if (!matched.includes(token)) matched.push(token);
    } else if (BEAR_WORDS.has(token)) {
      bearCount++;
      if (!matched.includes(token)) matched.push(token);
    }
  }

  const tone: "BULLISH" | "BEARISH" | "NEUTRAL" =
    bullCount > bearCount
      ? "BULLISH"
      : bearCount > bullCount
      ? "BEARISH"
      : "NEUTRAL";

  if (!cleanSummary) {
    cleanSummary = isIndirect
      ? `This sector and macroeconomic report from ${source} tracks industry-wide demand, supply-chain conditions, and regulatory catalysts that indirectly influence valuation and near-term price momentum.`
      : `This direct company report from ${source} covers primary operational, earnings, or market-moving developments for the target equity.`;
  }

  return {
    index,
    title: cleanTitle,
    summary: cleanSummary,
    source,
    url: cleanUrl,
    isIndirect,
    tone,
    matchedKeywords: matched.slice(0, 6),
  };
}

export default function MarketPulse({ sentimentData }: { sentimentData: any }) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const rawHeadlines =
    sentimentData?.top_headlines ||
    sentimentData?.news_headlines ||
    sentimentData?.headlines ||
    [];

  const parsedArticles: ParsedArticle[] = rawHeadlines.map(
    (item: any, idx: number) => parseHeadlineItem(item, idx)
  );

  const activeArticle =
    selectedIndex !== null && parsedArticles[selectedIndex]
      ? parsedArticles[selectedIndex]
      : null;

  const handlePrev = () => {
    if (selectedIndex === null || parsedArticles.length <= 1) return;
    setSelectedIndex(
      (selectedIndex - 1 + parsedArticles.length) % parsedArticles.length
    );
  };

  const handleNext = () => {
    if (selectedIndex === null || parsedArticles.length <= 1) return;
    setSelectedIndex((selectedIndex + 1) % parsedArticles.length);
  };

  return (
    <>
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
                Click any headline to read full article
              </p>
            </div>
          </div>
          {parsedArticles.length > 0 && (
            <span className="text-[10px] font-mono font-semibold text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded-md border border-teal-200 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              {parsedArticles.length} items
            </span>
          )}
        </div>

        {/* Headlines Feed */}
        <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2.5 pr-1 min-h-0">
          {parsedArticles.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 bg-slate-50/70 rounded-xl border border-dashed border-slate-200">
              <Newspaper className="w-6 h-6 text-slate-400" />
              <span className="text-xs text-slate-500 font-mono">
                Awaiting live market news...
              </span>
            </div>
          ) : (
            parsedArticles.map((article, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setSelectedIndex(i)}
                className="group text-left flex flex-col gap-1.5 p-3 rounded-xl border border-slate-200/80 bg-slate-50/70 hover:bg-white hover:border-teal-400 hover:shadow-sm transition-all duration-200 cursor-pointer animate-fade-in-up"
              >
                <div className="flex items-start justify-between gap-2 w-full">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <span
                      className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        article.isIndirect ? "bg-indigo-500" : "bg-teal-500"
                      }`}
                    />
                    <p className="text-xs font-semibold text-slate-900 group-hover:text-teal-700 font-sans leading-snug line-clamp-2 transition-colors">
                      {article.title}
                    </p>
                  </div>
                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase shrink-0 border ${
                      article.isIndirect
                        ? "text-indigo-700 bg-indigo-50 border-indigo-200"
                        : "text-teal-700 bg-teal-50 border-teal-200"
                    }`}
                  >
                    {article.isIndirect ? "Indirect • Sector" : "Direct"}
                  </span>
                </div>

                <p className="text-[11px] text-slate-500 font-sans leading-relaxed pl-4 line-clamp-1">
                  {article.summary}
                </p>

                <div className="flex items-center justify-between pl-4 pt-0.5">
                  <span className="text-[9px] font-mono text-slate-400 truncate max-w-[160px]">
                    {article.source}
                  </span>
                  <span className="text-[9px] font-mono font-semibold text-teal-600 opacity-75 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                    <BookOpen className="w-2.5 h-2.5" />
                    Read full story →
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ========= SMOOTH TRANSITION ARTICLE READER MODAL ========= */}
      {/* DialogContent already renders DialogPortal + DialogOverlay internally */}
      <Dialog
        open={activeArticle !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedIndex(null);
        }}
      >
        <DialogContent
          showCloseButton={false}
          className="bg-white border border-slate-200 rounded-2xl shadow-2xl p-0 sm:max-w-lg w-full overflow-hidden text-slate-900"
        >
          {activeArticle && (
            <div>
              {/* Top Accent Strip */}
              <div
                className={`h-1.5 ${
                  activeArticle.isIndirect
                    ? "bg-gradient-to-r from-indigo-600 via-violet-500 to-teal-500"
                    : "bg-gradient-to-r from-teal-600 via-emerald-500 to-cyan-500"
                }`}
              />

              <div className="p-6">
                {/* Top Meta Bar: Scope Badge + Sentiment Tone + Close Button */}
                <div className="flex items-center justify-between gap-2 pb-4 border-b border-slate-200">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[10px] font-mono font-bold px-2.5 py-1 rounded-lg uppercase border ${
                        activeArticle.isIndirect
                          ? "text-indigo-700 bg-indigo-50 border-indigo-200"
                          : "text-teal-700 bg-teal-50 border-teal-200"
                      }`}
                    >
                      {activeArticle.isIndirect
                        ? "Indirect • Sector & Macro Catalyst"
                        : "Direct • Company News"}
                    </span>

                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2.5 py-1 rounded-lg border ${
                        activeArticle.tone === "BULLISH"
                          ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                          : activeArticle.tone === "BEARISH"
                          ? "text-rose-700 bg-rose-50 border-rose-200"
                          : "text-amber-700 bg-amber-50 border-amber-200"
                      }`}
                    >
                      {activeArticle.tone === "BULLISH" ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : activeArticle.tone === "BEARISH" ? (
                        <TrendingDown className="w-3 h-3" />
                      ) : (
                        <Activity className="w-3 h-3" />
                      )}
                      {activeArticle.tone} SIGNAL
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => setSelectedIndex(null)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                    title="Close reader"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Source & Article Index */}
                <div className="flex items-center justify-between mt-3.5 mb-2 text-[11px] font-mono text-slate-500">
                  <span>
                    Source:{" "}
                    <strong className="text-slate-800">
                      {activeArticle.source}
                    </strong>
                  </span>
                  <span>
                    Article {activeArticle.index + 1} of {parsedArticles.length}
                  </span>
                </div>

                {/* Full Unclamped Headline */}
                <h3 className="text-base md:text-lg font-bold text-slate-900 font-sans leading-snug mb-4">
                  {activeArticle.title}
                </h3>

                {/* Full Scrollable Article Explanation / Story Body */}
                <div className="bg-slate-50 border border-slate-200/90 rounded-xl p-4 max-h-[240px] overflow-y-auto custom-scrollbar space-y-3">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500">
                    <BookOpen className="w-3.5 h-3.5 text-teal-600" />
                    <span>Full Article Summary &amp; Context</span>
                  </div>
                  <p className="text-xs md:text-sm text-slate-700 font-sans leading-relaxed whitespace-pre-line">
                    {activeArticle.summary}
                  </p>
                </div>

                {/* AI Lexical Signal Extraction Box */}
                <div className="mt-3.5 p-3 rounded-xl bg-slate-50/70 border border-slate-200/70 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono font-semibold text-slate-600">
                    <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                    <span>
                      Swarm Weight:{" "}
                      <strong className="text-slate-900">
                        {activeArticle.isIndirect
                          ? "0.6x (Indirect Sector)"
                          : "1.0x (Direct Asset)"}
                      </strong>
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-1">
                    {activeArticle.matchedKeywords.length > 0 ? (
                      activeArticle.matchedKeywords.map((kw) => (
                        <span
                          key={kw}
                          className="text-[9px] font-mono font-semibold px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700"
                        >
                          #{kw}
                        </span>
                      ))
                    ) : (
                      <span className="text-[9px] font-mono text-slate-400">
                        Neutral informational coverage
                      </span>
                    )}
                  </div>
                </div>

                {/* Footer Controls: Prev / Next Navigation + External Link + Close */}
                <div className="mt-5 pt-4 border-t border-slate-200 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={handlePrev}
                      disabled={parsedArticles.length <= 1}
                      className="flex items-center gap-1 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-xs font-semibold transition-colors cursor-pointer disabled:opacity-40"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      Prev
                    </button>
                    <button
                      type="button"
                      onClick={handleNext}
                      disabled={parsedArticles.length <= 1}
                      className="flex items-center gap-1 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-xs font-semibold transition-colors cursor-pointer disabled:opacity-40"
                    >
                      Next
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    {activeArticle.url && (
                      <a
                        href={activeArticle.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 font-mono text-xs font-bold transition-colors"
                      >
                        <span>Source Article</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                    <button
                      type="button"
                      onClick={() => setSelectedIndex(null)}
                      className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-mono text-xs font-bold transition-colors cursor-pointer"
                    >
                      Done
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
