"use client";

import React, { useState } from "react";
import { TrendingUp, TrendingDown, BarChart3, Activity } from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  YAxis,
  XAxis,
  Tooltip,
} from "recharts";

/* ── colour palette ───────────────────────────────────────────────── */

const BULL_COLOR = "#2dd4bf"; // teal – bullish
const BEAR_COLOR = "#f43f5e"; // rose – bearish

/* ── simple line tooltip ─────────────────────────────────────────── */

function LineTooltip({ active, payload, currencySymbol }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  const price = d.close ?? d.price ?? 0;
  const borderColor = "rgba(45, 212, 191, 0.25)";

  return (
    <div
      className="rounded-xl border bg-[#0a0e17]/95 px-3.5 py-2.5 backdrop-blur-xl shadow-2xl"
      style={{ borderColor }}
    >
      <p className="text-[10px] text-slate-400 font-mono mb-1 tracking-wider uppercase">
        {d.time || "—"}
      </p>
      <p className="text-sm font-bold font-mono text-slate-100">
        {currencySymbol}
        {Number(price).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </p>
    </div>
  );
}

/* ── main component ───────────────────────────────────────────────── */

export default function AssetIntelligence({ assetData }: { assetData: any }) {
  const [timeframe, setTimeframe] = useState("1M");
  const timeframes = ["1D", "5D", "15D", "1M"];

  /* ---------- awaiting state ---------- */
  if (!assetData) {
    return (
      <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-teal-400" />
            </div>
            <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-300 uppercase">
              Asset Intelligence
            </h2>
          </div>
          <span className="text-[9px] font-mono text-slate-600 bg-slate-900/60 px-2 py-0.5 rounded-md border border-slate-800/50">AWAITING</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-3">
          <div className="relative">
            <div className="w-12 h-12 rounded-full border-2 border-teal-500/20 flex items-center justify-center animate-float">
              <BarChart3 className="w-5 h-5 text-teal-500/40" />
            </div>
            <div className="absolute inset-0 rounded-full bg-teal-400/5 blur-xl animate-glow-pulse" />
          </div>
          <span className="text-slate-500 font-mono text-xs">Awaiting Swarm Market Telemetry...</span>
        </div>
      </div>
    );
  }

  /* ---------- data extraction ---------- */
  const timeframeData = assetData.timeframe_data || {};
  const allChartData = assetData.chart_data || assetData.chart || assetData.historical_data || [];
  const rawData: any[] = timeframeData[timeframe] || allChartData;

  // Use close/price for the line chart
  const chartData = rawData.map((d: any) => ({
    ...d,
    value: d.close ?? d.price ?? 0,
  }));

  const price = assetData.current_price || assetData.price || "0.00";
  const volatility = assetData.volatility || "0.00";
  const changePct = assetData.change_pct;
  const trend =
    changePct !== undefined && changePct !== null
      ? `${changePct >= 0 ? "+" : ""}${Number(changePct).toFixed(2)}%`
      : assetData.trend || "+0.00%";
  const ticker = assetData.ticker || assetData.symbol || "N/A";
  const isPositive = assetData.is_positive ?? true;

  const currency = assetData.currency || "USD";
  const currencySymbol = currency === "INR" ? "₹" : "$";
  const formattedPrice =
    currency === "INR"
      ? Number(price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : Number(price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const lineColor = isPositive ? BULL_COLOR : BEAR_COLOR;
  const gradientId = "assetLineGradient";

  return (
    <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15 group-hover:border-teal-500/30">
            <Activity className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div>
            <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
              Asset Intelligence
            </h2>
            <span className="text-[10px] font-mono text-teal-400/70">{ticker}</span>
          </div>
        </div>
        <div className="flex gap-1 bg-slate-900/50 p-0.5 rounded-lg border border-slate-800/50">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`text-[10px] font-mono px-2.5 py-1 rounded-md transition-all duration-300 cursor-pointer ${
                timeframe === tf
                  ? "bg-teal-500/15 text-teal-400 shadow-sm shadow-teal-500/10"
                  : "text-slate-500 hover:text-slate-300 hover:bg-slate-800/50"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Area — Simple Line Chart */}
      <div className="relative flex-1 w-full min-h-[120px] mt-1 rounded-xl bg-[#030508]/80 overflow-hidden border border-slate-800/30">
        {chartData.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
            <BarChart3 className="w-5 h-5 text-slate-700" />
            <span className="text-[10px] font-mono uppercase tracking-widest text-slate-600">No Chart Data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 12, right: 12, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={lineColor} stopOpacity={0.25} />
                  <stop offset="50%" stopColor={lineColor} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                tick={{ fill: "#475569", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={["dataMin - 1", "dataMax + 1"]}
                hide
              />
              <Tooltip
                content={<LineTooltip currencySymbol={currencySymbol} />}
                cursor={{
                  stroke: "rgba(45, 212, 191, 0.12)",
                  strokeWidth: 1,
                  strokeDasharray: "4 4",
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={lineColor}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                animationDuration={800}
                animationEasing="ease-out"
                dot={false}
                activeDot={{
                  r: 4,
                  stroke: lineColor,
                  strokeWidth: 2,
                  fill: "#0a0e17",
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 mt-4">
        <div className="stat-value text-center flex flex-col items-center justify-center p-2 rounded-xl bg-slate-900/30 border border-slate-800/30 cursor-default">
          <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase mb-1">Price</span>
          <span className="text-base font-bold text-slate-100 font-mono">
            {currencySymbol}{formattedPrice}
          </span>
        </div>
        <div className="stat-value text-center flex flex-col items-center justify-center p-2 rounded-xl bg-slate-900/30 border border-slate-800/30 cursor-default">
          <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase mb-1">Volatility</span>
          <span className="text-base font-bold text-slate-100 font-mono">{volatility}%</span>
        </div>
        <div className="stat-value text-center flex flex-col items-center justify-center p-2 rounded-xl bg-slate-900/30 border border-slate-800/30 cursor-default">
          <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase mb-1">Trend</span>
          <div className="flex items-center gap-1">
            {isPositive ? (
              <TrendingUp className="w-3.5 h-3.5 text-teal-400" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className={`text-base font-bold font-mono ${isPositive ? "text-teal-400" : "text-rose-400"}`}>
              {trend}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
