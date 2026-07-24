"use client";
import React from "react";
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";
import { Activity } from "lucide-react";

// Pass `assetData` down from your main WebSocket hook when `type === "asset_intelligence"`
export default function AssetIntelligence({ assetData }: { assetData: any }) {
  
  // 1. STANDBY STATE (Before Parser finishes)
  if (!assetData) {
    return (
      <div className="w-full rounded-xl border border-slate-800 bg-[#070A12] p-5 shadow-2xl backdrop-blur-md min-h-[300px] flex flex-col justify-between">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Asset Intelligence - Awaiting Directive
          </h2>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-slate-600 font-mono text-xs">
          <Activity className="w-8 h-8 mb-2 opacity-50 animate-pulse" />
          <p className="italic">Graph inactive. Nexus is on standby.</p>
        </div>
      </div>
    );
  }

  // 2. ACTIVE STATE
  const { ticker, current_price, change, change_pct, volatility, is_positive, chart_data } = assetData;
  
  // Dynamic color routing
  const trendColor = is_positive ? "#10B981" : "#EF4444"; 
  const riskColor = volatility > 25 ? "text-red-400" : volatility > 15 ? "text-amber-400" : "text-emerald-400";
  const riskLabel = volatility > 25 ? "High Risk" : volatility > 15 ? "Med Risk" : "Low Risk";

  return (
    <div className="w-full rounded-xl border border-slate-800 bg-[#070A12] p-5 shadow-2xl backdrop-blur-md min-h-[300px] flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
        <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
          Asset Intelligence - {ticker}
        </h2>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-slate-500 text-xs font-mono mb-1">Current Price</p>
          <p className="text-xl font-bold text-slate-100">${current_price.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-slate-500 text-xs font-mono mb-1">Change</p>
          <p className={`text-sm font-bold ${is_positive ? 'text-emerald-400' : 'text-red-400'}`}>
            {is_positive ? "+" : ""}{change.toFixed(2)} ({is_positive ? "+" : ""}{change_pct.toFixed(2)}%)
          </p>
        </div>
        <div className="text-right">
          <p className="text-slate-500 text-xs font-mono mb-1">30-Day Volatility</p>
          <p className={`text-sm font-bold ${riskColor}`}>
            {volatility.toFixed(1)}% {riskLabel}
          </p>
        </div>
      </div>

      <div className="flex-1 w-full h-40 bg-[#030509] rounded-lg border border-slate-800/90 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chart_data}>
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={trendColor} stopOpacity={0.4} />
                <stop offset="95%" stopColor={trendColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" hide />
            <YAxis domain={['auto', 'auto']} hide />
            <Tooltip 
              contentStyle={{ backgroundColor: '#0B0F19', borderColor: '#1E293B', color: '#F1F5F9' }} 
              itemStyle={{ color: trendColor, fontWeight: 'bold' }}
              labelStyle={{ color: '#94A3B8' }}
            />
            <Area 
              type="monotone" 
              dataKey="price" 
              stroke={trendColor} 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorGradient)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
