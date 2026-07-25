"use client";

import React, { useState } from "react";
import { LineChart } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, YAxis } from "recharts";

export default function AssetIntelligence({ assetData }: { assetData: any }) {
  const [timeframe, setTimeframe] = useState("1M");
  
  // Custom timeframes as requested
  const timeframes = ["1D", "5D", "15D", "1M", "ALL"];

  // Fallback mock data to prevent crashes if backend sends nothing
  const data = assetData?.chart || [
    { price: 310 }, { price: 315 }, { price: 312 }, { price: 320 }, { price: 333.02 }
  ];

  const price = assetData?.price || "333.02";
  const volatility = assetData?.volatility || "30.09%";
  const trend = assetData?.trend || "+21.03%";
  const ticker = assetData?.ticker || "AAPL";

  return (
    <div className="w-full h-full rounded-2xl border border-slate-800/80 bg-[#0A0E17]/80 p-5 flex flex-col shadow-2xl backdrop-blur-md">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
        <div className="flex items-center gap-2">
          <LineChart className="w-4 h-4 text-teal-400" />
          <h2 className="text-xs tracking-widest font-mono font-bold text-slate-200 uppercase">
            Asset Intelligence: [{ticker}]
          </h2>
        </div>
        <div className="flex gap-2">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`text-[10px] font-mono px-2 py-1 rounded transition-all cursor-pointer ${
                timeframe === tf
                  ? "bg-teal-500/20 text-teal-400 border border-teal-500/50"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 w-full min-h-[150px] mt-2 border border-slate-800/50 rounded-xl bg-[#05080F] overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2dd4bf" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#2dd4bf" stopOpacity={0} />
              </linearGradient>
            </defs>
            <YAxis domain={['auto', 'auto']} hide />
            <Area 
              type="monotone" 
              dataKey="price" 
              stroke="#2dd4bf" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorPrice)" 
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-4 mt-5">
        <div className="text-center flex flex-col items-center justify-center">
          <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase mb-1">Price</span>
          <span className="text-lg font-bold text-slate-100 font-mono">${price}</span>
        </div>
        <div className="text-center flex flex-col items-center justify-center">
          <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase mb-1">Volatility</span>
          <span className="text-lg font-bold text-slate-100 font-mono">{volatility}</span>
        </div>
        <div className="text-center flex flex-col items-center justify-center">
          <span className="text-[10px] text-slate-500 font-mono tracking-widest uppercase mb-1">Trend</span>
          <span className="text-lg font-bold text-teal-400 font-mono">{trend}</span>
        </div>
      </div>
    </div>
  );
}
