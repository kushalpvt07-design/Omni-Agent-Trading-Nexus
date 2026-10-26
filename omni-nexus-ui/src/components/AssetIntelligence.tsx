"use client";

import React, { useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  CandlestickChart,
  LineChart as LineChartIcon,
} from "lucide-react";
import {
  ComposedChart,
  Area,
  Line,
  Bar,
  ResponsiveContainer,
  YAxis,
  XAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

const BULL_COLOR = "#059669"; // Emerald 600
const BEAR_COLOR = "#E11D48"; // Rose 600
const SMA_COLOR = "#4F46E5";  // Indigo 600

function CustomChartTooltip({ active, payload, currencySymbol }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  const price = d.close ?? d.price ?? 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 px-3.5 py-2.5 shadow-lg backdrop-blur-md">
      <p className="text-[10px] text-slate-500 font-mono mb-1 uppercase font-semibold">
        {d.time || "—"}
      </p>
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-bold font-mono text-slate-900">
          {currencySymbol}
          {Number(price).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </span>
        {d.sma !== undefined && (
          <span className="text-[10px] font-mono text-indigo-600 font-medium">
            SMA(30): {currencySymbol}
            {Number(d.sma).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        )}
      </div>
      {d.high !== undefined && d.low !== undefined && (
        <div className="flex gap-2.5 mt-1.5 pt-1.5 border-t border-slate-100 text-[10px] font-mono text-slate-600">
          <span>
            O: {currencySymbol}
            {Number(d.open).toFixed(2)}
          </span>
          <span className="text-emerald-600 font-semibold">
            H: {currencySymbol}
            {Number(d.high).toFixed(2)}
          </span>
          <span className="text-rose-600 font-semibold">
            L: {currencySymbol}
            {Number(d.low).toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
}

export default function AssetIntelligence({ assetData }: { assetData: any }) {
  const [timeframe, setTimeframe] = useState("1M");
  const [chartMode, setChartMode] = useState<"area" | "ohlc">("area");
  const timeframes = ["1D", "5D", "15D", "1M", "ALL"];

  if (!assetData) {
    return (
      <div className="w-full h-full rounded-2xl bento-card p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-teal-600" />
            </div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-800 uppercase">
              Asset Intelligence &amp; Technical Telemetry
            </h2>
          </div>
          <span className="text-[9px] font-mono text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-md border border-slate-200">
            STANDBY
          </span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center gap-2.5 bg-slate-50/70 rounded-xl border border-dashed border-slate-200">
          <BarChart3 className="w-7 h-7 text-slate-400" />
          <span className="text-slate-500 font-mono text-xs">
            Deploy a directive to stream live price, 30D SMA, RSI(14), and OHLC telemetry.
          </span>
        </div>
      </div>
    );
  }

  const timeframeData = assetData.timeframe_data || {};
  const allChartData = assetData.chart_data || [];
  const rawData: any[] = timeframeData[timeframe] || allChartData;

  const priceNum = Number(assetData.current_price || assetData.price || 0);
  const sma30Num = Number(assetData.thirty_day_sma || priceNum);
  const rsiNum = Number(assetData.rsi_14 ?? 50);
  const volRatioNum = Number(assetData.volume_ratio_30d ?? 1.0);
  const volatility = Number(assetData.volatility || 0).toFixed(2);
  const changePct = Number(assetData.change_pct || 0);
  const ticker = assetData.ticker || "N/A";
  const isPositive = assetData.is_positive ?? changePct >= 0;

  const currency = assetData.currency || "USD";
  const currencySymbol = currency === "INR" ? "₹" : "$";

  const chartData = rawData.map((d: any) => {
    const closeVal = Number(d.close ?? d.price ?? 0);
    const lowVal = Number(d.low ?? closeVal);
    const highVal = Number(d.high ?? closeVal);
    return {
      ...d,
      value: closeVal,
      sma: d.sma !== undefined ? Number(d.sma) : sma30Num,
      ohlc_range: [lowVal, highVal],
    };
  });

  const lineColor = isPositive ? BULL_COLOR : BEAR_COLOR;
  const rsiLabel =
    rsiNum >= 70 ? "Overbought" : rsiNum <= 35 ? "Near Oversold" : "Neutral";
  const rsiBadgeStyle =
    rsiNum >= 70
      ? "bg-rose-50 text-rose-700 border-rose-200"
      : rsiNum <= 35
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-emerald-50 text-emerald-700 border-emerald-200";

  return (
    <div className="w-full h-full rounded-2xl bento-card p-5 flex flex-col">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200/80 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center">
            <Activity className="w-4 h-4 text-teal-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs tracking-wider font-mono font-bold text-slate-900 uppercase">
                {ticker}
              </h2>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                {currency}
              </span>
              <span className="text-[10px] font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200 hidden sm:inline">
                - - 30D SMA ({currencySymbol}{sma30Num.toFixed(2)})
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-500">
              Real-Time Price vs. 30-Day Moving Average &amp; OHLC Range
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Chart Mode Toggle: Area vs OHLC */}
          <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              type="button"
              onClick={() => setChartMode("area")}
              className={`flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded-md transition-all cursor-pointer ${
                chartMode === "area"
                  ? "bg-white text-slate-900 shadow-2xs font-semibold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="Price + 30D SMA Line"
            >
              <LineChartIcon className="w-3 h-3" />
              <span>SMA</span>
            </button>
            <button
              type="button"
              onClick={() => setChartMode("ohlc")}
              className={`flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded-md transition-all cursor-pointer ${
                chartMode === "ohlc"
                  ? "bg-white text-slate-900 shadow-2xs font-semibold"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="Daily High-Low OHLC Range + Close"
            >
              <CandlestickChart className="w-3 h-3" />
              <span>OHLC</span>
            </button>
          </div>

          {/* Timeframes */}
          <div className="flex gap-0.5 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            {timeframes.map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={`text-[10px] font-mono px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  timeframe === tf
                    ? "bg-white text-teal-700 font-bold shadow-2xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="relative flex-1 w-full min-h-[175px] rounded-xl bg-slate-50/70 border border-slate-200/70 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 12, left: 0, bottom: 2 }}
          >
            <defs>
              <linearGradient id="daylightPriceGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={lineColor} stopOpacity={0.22} />
                <stop offset="100%" stopColor={lineColor} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="time"
              tick={{ fill: "#64748B", fontSize: 10, fontFamily: "var(--font-mono)" }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis domain={["auto", "auto"]} hide />
            <Tooltip content={<CustomChartTooltip currencySymbol={currencySymbol} />} />

            {chartMode === "ohlc" && (
              <Bar
                dataKey="ohlc_range"
                fill={lineColor}
                opacity={0.35}
                barSize={6}
                radius={[3, 3, 3, 3]}
              />
            )}

            <Area
              type="monotone"
              dataKey="value"
              stroke={lineColor}
              strokeWidth={2.2}
              fill="url(#daylightPriceGrad)"
              dot={false}
              activeDot={{ r: 4, stroke: lineColor, strokeWidth: 2, fill: "#FFFFFF" }}
            />

            {/* Dashed Indigo 30-Day SMA Overlay */}
            <Line
              type="monotone"
              dataKey="sma"
              stroke={SMA_COLOR}
              strokeWidth={1.75}
              strokeDasharray="5 5"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 4-Metric Quantitative Telemetry Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-3.5">
        {/* 1. Live Price & Trend */}
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">
              Live Price
            </span>
            <span
              className={`flex items-center gap-0.5 text-[10px] font-mono font-bold ${
                isPositive ? "text-emerald-600" : "text-rose-600"
              }`}
            >
              {isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              {changePct >= 0 ? "+" : ""}
              {changePct.toFixed(2)}%
            </span>
          </div>
          <p className="text-sm md:text-base font-bold font-mono text-slate-900">
            {currencySymbol}
            {priceNum.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>

        {/* 2. Annualized Log Volatility */}
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">
              30D Log Volatility
            </span>
            <span className="text-[9px] font-mono text-slate-400">Ann.</span>
          </div>
          <p className="text-sm md:text-base font-bold font-mono text-slate-900">
            {volatility}%
          </p>
        </div>

        {/* 3. Wilder RSI (14) */}
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">
              Wilder RSI(14)
            </span>
            <span
              className={`text-[8px] font-mono font-semibold px-1.5 py-0.2 rounded border ${rsiBadgeStyle}`}
            >
              {rsiLabel}
            </span>
          </div>
          <p className="text-sm md:text-base font-bold font-mono text-slate-900">
            {rsiNum.toFixed(2)}
          </p>
        </div>

        {/* 4. Volume vs 30D Avg */}
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">
              Rel. Volume
            </span>
            <span className="text-[9px] font-mono text-teal-700 font-semibold">
              vs 30D Avg
            </span>
          </div>
          <p className="text-sm md:text-base font-bold font-mono text-slate-900">
            {volRatioNum.toFixed(2)}x
          </p>
        </div>
      </div>
    </div>
  );
}
