"use client";

import React from "react";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Landmark,
  Coins,
  BarChart3,
} from "lucide-react";
import { PortfolioData } from "@/types/swarm";

export default function PortfolioLedger({
  portfolioData,
}: {
  portfolioData: PortfolioData | null;
}) {
  // ── Empty / Loading State ───────────────────────────────────
  if (!portfolioData) {
    return (
      <div className="w-full rounded-2xl glass-card gradient-border p-5 flex flex-col group">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
              <Wallet className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-300 uppercase">
              Portfolio Ledger
            </h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-6">
          <div className="relative">
            <div className="w-12 h-12 rounded-full border-2 border-violet-500/15 flex items-center justify-center animate-float">
              <Wallet className="w-5 h-5 text-violet-500/30" />
            </div>
            <div className="absolute inset-0 rounded-full bg-violet-400/5 blur-xl animate-glow-pulse" />
          </div>
          <span className="text-slate-500 font-mono text-xs">
            Connecting to ledger...
          </span>
        </div>
      </div>
    );
  }

  const { cash, total_value, positions } = portfolioData;
  const holdingsValue = total_value - cash;
  const hasPositions = positions.length > 0;

  return (
    <div className="w-full rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-violet-500/15">
            <Wallet className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Portfolio Ledger
          </h2>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-violet-400/80 bg-violet-950/20 px-2.5 py-1 rounded-lg border border-violet-500/15 transition-all duration-300 hover:border-violet-500/30">
          <BarChart3 className="w-3 h-3 text-violet-400" />
          <span>{positions.length} holding{positions.length !== 1 ? "s" : ""}</span>
        </div>
      </div>

      {/* ── Summary Row ────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-2.5 mb-3">
        {/* Total Value */}
        <div className="bg-[#030508]/60 rounded-xl border border-slate-800/30 p-2.5 text-center transition-all duration-300 hover:border-violet-500/15">
          <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
            <Landmark className="w-2.5 h-2.5" />
            Total Value
          </p>
          <p className="text-sm font-bold font-mono text-slate-100 tracking-wide">
            ${total_value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        {/* Cash */}
        <div className="bg-[#030508]/60 rounded-xl border border-slate-800/30 p-2.5 text-center transition-all duration-300 hover:border-teal-500/15">
          <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
            <Coins className="w-2.5 h-2.5" />
            Cash
          </p>
          <p className="text-sm font-bold font-mono text-teal-400 tracking-wide">
            ${cash.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        {/* Holdings */}
        <div className="bg-[#030508]/60 rounded-xl border border-slate-800/30 p-2.5 text-center transition-all duration-300 hover:border-cyan-500/15">
          <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
            <BarChart3 className="w-2.5 h-2.5" />
            Holdings
          </p>
          <p className="text-sm font-bold font-mono text-cyan-400 tracking-wide">
            ${holdingsValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* ── Positions Table ────────────────────────────────── */}
      <div className="flex-1 min-h-[80px] max-h-[180px] bg-[#020406]/60 rounded-xl border border-slate-800/30 overflow-y-auto custom-scrollbar relative">
        {/* Gradient left accent line */}
        <div className="absolute left-0 top-0 bottom-0 w-[2px] rounded-full bg-gradient-to-b from-violet-500/40 via-violet-500/10 to-transparent" />

        {!hasPositions ? (
          <div className="h-full flex items-center justify-center">
            <p className="text-slate-600 italic text-[11px] flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-700" />
              No open positions
            </p>
          </div>
        ) : (
          <table className="w-full text-[10px] font-mono">
            <thead className="sticky top-0 bg-[#0a0e17]/95 backdrop-blur-sm z-10">
              <tr className="border-b border-slate-800/40 text-slate-500 uppercase tracking-wider">
                <th className="text-left py-2 px-3 font-semibold">Ticker</th>
                <th className="text-right py-2 px-3 font-semibold">Shares</th>
                <th className="text-right py-2 px-3 font-semibold">Price</th>
                <th className="text-right py-2 px-3 font-semibold">Value</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos, index) => {
                const isPositive = pos.current_price > 0;
                return (
                  <tr
                    key={pos.ticker}
                    className="border-b border-slate-800/20 transition-all duration-200 hover:bg-violet-500/[0.03] animate-fade-in-up"
                    style={{ animationDelay: `${index * 0.06}s` }}
                  >
                    <td className="py-1.5 px-3">
                      <div className="flex items-center gap-1.5">
                        {isPositive ? (
                          <TrendingUp className="w-2.5 h-2.5 text-teal-500/60" />
                        ) : (
                          <TrendingDown className="w-2.5 h-2.5 text-rose-500/60" />
                        )}
                        <span className="text-slate-200 font-semibold">{pos.ticker}</span>
                      </div>
                    </td>
                    <td className="py-1.5 px-3 text-right text-slate-400">
                      {pos.shares.toLocaleString("en-US", { maximumFractionDigits: 4 })}
                    </td>
                    <td className="py-1.5 px-3 text-right text-slate-400">
                      ${pos.current_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-1.5 px-3 text-right">
                      <span className={`font-semibold ${pos.market_value > 0 ? 'text-teal-400' : 'text-slate-500'}`}>
                        ${pos.market_value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
