"use client";

import React, { useState, useMemo } from "react";
import { LineChart, AlertCircle, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, YAxis, Tooltip, XAxis, CartesianGrid } from "recharts";

const TIMEFRAME_COLORS: Record<string, { stroke: string; fill: string; label: string }> = {
  "1D": { stroke: "#a78bfa", fill: "rgba(167, 139, 250, 0.12)", label: "1 Day" },
  "5D": { stroke: "#38bdf8", fill: "rgba(56, 189, 248, 0.12)", label: "5 Days" },
  "15D": { stroke: "#fb923c", fill: "rgba(251, 146, 60, 0.12)", label: "15 Days" },
  "1M": { stroke: "#2dd4bf", fill: "rgba(45, 212, 191, 0.12)", label: "1 Month" },
};

const CustomTooltip = ({ active, payload, label, currencySymbol }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-teal-500/20 bg-[#0a0e17]/95 px-3 py-2.5 backdrop-blur-xl shadow-2xl shadow-teal-500/5">
        <p className="text-[10px] text-slate-400 font-mono mb-1">{label || "Time"}</p>
        <p className="text-sm text-teal-400 font-bold font-mono">{currencySymbol}{Number(payload[0].value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
      </div>
    );
  }
  return null;
};

/** A single mini-chart used in the ALL grid view */
function MiniChart({ data, color, title, currencySymbol }: { data: any[]; color: typeof TIMEFRAME_COLORS["1D"]; title: string; currencySymbol: string }) {
  return (
    <div className="flex flex-col rounded-lg bg-[#030508]/80 border border-slate-800/30 p-2 h-full">
      <span className="text-[9px] font-mono tracking-wider uppercase mb-1" style={{ color: color.stroke }}>{title}</span>
      <div className="flex-1 min-h-0">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-[8px] font-mono text-slate-600">No data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`fill-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color.stroke} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={color.stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis domain={['auto', 'auto']} hide />
              <Tooltip content={<CustomTooltip currencySymbol={currencySymbol} />} />
              <Area
                type="monotone"
                dataKey="price"
                stroke={color.stroke}
                strokeWidth={1.5}
                fillOpacity={1}
                fill={`url(#fill-${title})`}
                isAnimationActive={true}
                animationDuration={800}
                dot={false}
                activeDot={{ r: 3, stroke: color.stroke, strokeWidth: 1.5, fill: '#0a0e17' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export default function AssetIntelligence({ assetData }: { assetData: any }) {
  const [timeframe, setTimeframe] = useState("1M");
  const timeframes = ["1D", "5D", "15D", "1M", "ALL"];

  if (!assetData) {
    return (
      <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <LineChart className="w-3.5 h-3.5 text-teal-400" />
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

  // Failsafe key extractions — aligned to the backend's actual payload shape from utils.py
  const timeframeData = assetData.timeframe_data || {};
  const allChartData = assetData.chart_data || assetData.chart || assetData.historical_data || [];
  // Use timeframe-specific data if available, otherwise fall back to the default chart_data
  const data = timeframeData[timeframe] || allChartData;
  const price = assetData.current_price || assetData.price || "0.00";
  const volatility = assetData.volatility || "0.00";
  const changePct = assetData.change_pct;
  const trend = changePct !== undefined && changePct !== null
    ? `${changePct >= 0 ? "+" : ""}${Number(changePct).toFixed(2)}%`
    : (assetData.trend || "+0.00%");
  const ticker = assetData.ticker || assetData.symbol || "N/A";
  const isPositive = assetData.is_positive ?? true;

  // Currency detection — ₹ for Indian stocks, $ for everything else
  const currency = assetData.currency || "USD";
  const currencySymbol = currency === "INR" ? "₹" : "$";

  // Format price with proper locale (Indian numbering for INR)
  const formattedPrice = currency === "INR"
    ? Number(price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : Number(price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Check if ALL view should show multi-graph
  const isAllView = timeframe === "ALL";

  return (
    <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15 group-hover:border-teal-500/30">
            <LineChart className="w-3.5 h-3.5 text-teal-400" />
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

      {/* Chart Area */}
      <div className="relative flex-1 w-full min-h-[120px] mt-1 rounded-xl bg-[#030508]/80 overflow-hidden border border-slate-800/30">
        {isAllView ? (
          /* ALL view: 2x2 grid of mini-charts with different colors */
          <div className="grid grid-cols-2 grid-rows-2 gap-2 p-2 h-full">
            {(["1D", "5D", "15D", "1M"] as const).map((tf) => (
              <MiniChart
                key={tf}
                data={timeframeData[tf] || allChartData}
                color={TIMEFRAME_COLORS[tf]}
                title={TIMEFRAME_COLORS[tf].label}
                currencySymbol={currencySymbol}
              />
            ))}
          </div>
        ) : data.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 gap-2">
            <AlertCircle className="w-5 h-5 text-rose-900/70" />
            <span className="text-[10px] font-mono uppercase tracking-widest text-slate-600">No Chart Data In Payload</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isPositive ? "#2dd4bf" : "#f43f5e"} stopOpacity={0.25} />
                  <stop offset="50%" stopColor={isPositive ? "#2dd4bf" : "#f43f5e"} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={isPositive ? "#2dd4bf" : "#f43f5e"} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="strokeGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={isPositive ? "#14b8a6" : "#e11d48"} />
                  <stop offset="50%" stopColor={isPositive ? "#2dd4bf" : "#f43f5e"} />
                  <stop offset="100%" stopColor={isPositive ? "#06b6d4" : "#fb7185"} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51, 65, 85, 0.15)" vertical={false} />
              <XAxis 
                dataKey="time" 
                tick={{ fill: '#475569', fontSize: 9, fontFamily: 'var(--font-mono)' }} 
                axisLine={false} 
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis domain={['auto', 'auto']} hide />
              <Tooltip 
                content={<CustomTooltip currencySymbol={currencySymbol} />} 
                cursor={{ stroke: 'rgba(45, 212, 191, 0.15)', strokeWidth: 1, strokeDasharray: '4 4' }} 
              />
              <Area 
                type="monotone" 
                dataKey="price" 
                stroke="url(#strokeGrad)" 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorPrice)" 
                isAnimationActive={true}
                animationDuration={1200}
                animationEasing="ease-out"
                dot={false}
                activeDot={{ r: 4, stroke: isPositive ? '#2dd4bf' : '#f43f5e', strokeWidth: 2, fill: '#0a0e17' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 mt-4">
        <div className="stat-value text-center flex flex-col items-center justify-center p-2 rounded-xl bg-slate-900/30 border border-slate-800/30 cursor-default">
          <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase mb-1">Price</span>
          <span className="text-base font-bold text-slate-100 font-mono">{currencySymbol}{formattedPrice}</span>
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
            <span className={`text-base font-bold font-mono ${isPositive ? "text-teal-400" : "text-rose-400"}`}>{trend}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
