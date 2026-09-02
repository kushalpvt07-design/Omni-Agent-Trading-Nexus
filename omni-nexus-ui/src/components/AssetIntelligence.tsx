"use client";

import React, { useState, useMemo } from "react";
import { CandlestickChart, AlertCircle, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import {
  ComposedChart,
  Bar,
  ResponsiveContainer,
  YAxis,
  XAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ReferenceLine,
} from "recharts";

/* ── colour palette ───────────────────────────────────────────────── */

const BULL_COLOR = "#2dd4bf"; // teal – bullish
const BULL_COLOR_DIM = "rgba(45, 212, 191, 0.35)";
const BEAR_COLOR = "#f43f5e"; // rose – bearish
const BEAR_COLOR_DIM = "rgba(244, 63, 94, 0.35)";
const DOJI_COLOR = "#64748b"; // slate – flat candle

const TIMEFRAME_COLORS: Record<string, { bull: string; bear: string; label: string }> = {
  "1D": { bull: "#a78bfa", bear: "#c084fc", label: "1 Day" },
  "5D": { bull: "#38bdf8", bear: "#7dd3fc", label: "5 Days" },
  "15D": { bull: "#fb923c", bear: "#fdba74", label: "15 Days" },
  "1M": { bull: "#2dd4bf", bear: "#5eead4", label: "1 Month" },
};

/* ── helpers ──────────────────────────────────────────────────────── */

/** Enrich data points with candlestick-specific computed fields */
function enrichCandleData(data: any[]) {
  return data.map((d, i) => {
    const open = d.open ?? d.price;
    const close = d.close ?? d.price;
    const high = d.high ?? Math.max(open, close);
    const low = d.low ?? Math.min(open, close);
    const isBull = close >= open;

    // The bar spans from open to close (body)
    const bodyLow = Math.min(open, close);
    const bodyHigh = Math.max(open, close);
    // Ensure body has at least a tiny height so doji candles are visible
    const bodyHeight = bodyHigh - bodyLow || 0.001;

    return {
      ...d,
      open,
      close,
      high,
      low,
      isBull,
      // For the bar: we use a trick — bar starts at bodyLow with height bodyHeight
      bodyLow,
      bodyHeight,
      wickHigh: high,
      wickLow: low,
    };
  });
}

/* ── custom candlestick shape ─────────────────────────────────────── */

interface CandleShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: any;
  yAxis?: any;
  background?: any;
}

function CandleShape(props: CandleShapeProps) {
  const { x = 0, width = 0, payload } = props;
  if (!payload) return null;

  const { open, close, high, low, isBull } = payload;
  const bodyLow = Math.min(open, close);
  const bodyHigh = Math.max(open, close);

  // We need access to the Y-axis scale. Recharts passes it indirectly via 
  // the y, height props which map to bodyLow and bodyHeight in data coords.
  // We can compute the y scale factor from the bar's rendered y & height vs data values.
  const bodyDataHeight = bodyHigh - bodyLow || 0.001;
  const renderedY = props.y ?? 0;
  const renderedH = Math.max(Math.abs(props.height ?? 0), 1); // ensure min 1px body

  const pixelsPerUnit = renderedH / bodyDataHeight;

  // Wick coordinates  
  const wickTopY = renderedY - (high - bodyHigh) * pixelsPerUnit;
  const wickBottomY = renderedY + renderedH + (bodyLow - low) * pixelsPerUnit;

  const centerX = x + width / 2;
  const wickWidth = Math.max(1, width * 0.12);
  const bodyWidth = Math.max(2, width * 0.65);
  const bodyX = centerX - bodyWidth / 2;

  const fillColor = isBull ? BULL_COLOR : BEAR_COLOR;
  const fillColorDim = isBull ? BULL_COLOR_DIM : BEAR_COLOR_DIM;
  const isDoji = Math.abs(open - close) < 0.001;

  return (
    <g>
      {/* Wick (shadow) */}
      <rect
        x={centerX - wickWidth / 2}
        y={wickTopY}
        width={wickWidth}
        height={Math.max(wickBottomY - wickTopY, 0.5)}
        fill={isDoji ? DOJI_COLOR : fillColor}
        rx={0.5}
        opacity={0.7}
      />
      {/* Body */}
      <rect
        x={bodyX}
        y={renderedY}
        width={bodyWidth}
        height={Math.max(renderedH, 1)}
        fill={isDoji ? DOJI_COLOR : (isBull ? fillColorDim : fillColor)}
        stroke={isDoji ? DOJI_COLOR : fillColor}
        strokeWidth={1}
        rx={1}
      />
      {/* Glow effect on hover-friendly candles */}
      <rect
        x={bodyX - 1}
        y={renderedY - 1}
        width={bodyWidth + 2}
        height={Math.max(renderedH, 1) + 2}
        fill="none"
        stroke={fillColor}
        strokeWidth={0}
        rx={2}
        className="transition-all duration-200"
        opacity={0}
      />
    </g>
  );
}

/* ── custom OHLC tooltip ─────────────────────────────────────────── */

function CandleTooltip({ active, payload, label, currencySymbol }: any) {
  if (active && payload && payload.length) {
    const d = payload[0]?.payload;
    if (!d) return null;
    const isBull = (d.close ?? d.price) >= (d.open ?? d.price);
    const borderColor = isBull ? "rgba(45, 212, 191, 0.3)" : "rgba(244, 63, 94, 0.3)";
    const accentColor = isBull ? BULL_COLOR : BEAR_COLOR;

    return (
      <div
        className="rounded-xl border bg-[#0a0e17]/95 px-3.5 py-3 backdrop-blur-xl shadow-2xl"
        style={{ borderColor }}
      >
        <p className="text-[10px] text-slate-400 font-mono mb-2 tracking-wider uppercase">
          {label || d.time || "—"}
        </p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {[
            { label: "Open", val: d.open },
            { label: "High", val: d.high },
            { label: "Low", val: d.low },
            { label: "Close", val: d.close ?? d.price },
          ].map((item) => (
            <div key={item.label} className="flex items-center justify-between gap-2">
              <span className="text-[9px] text-slate-500 font-mono">{item.label}</span>
              <span className="text-[11px] font-bold font-mono" style={{ color: accentColor }}>
                {currencySymbol}
                {Number(item.val).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
}

/* ── mini candlestick chart for ALL view ──────────────────────────── */

function MiniCandleChart({
  data,
  colors,
  title,
  currencySymbol,
}: {
  data: any[];
  colors: typeof TIMEFRAME_COLORS["1D"];
  title: string;
  currencySymbol: string;
}) {
  const enriched = useMemo(() => enrichCandleData(data), [data]);

  return (
    <div className="flex flex-col rounded-lg bg-[#030508]/80 border border-slate-800/30 p-2 h-full">
      <span
        className="text-[9px] font-mono tracking-wider uppercase mb-1"
        style={{ color: colors.bull }}
      >
        {title}
      </span>
      <div className="flex-1 min-h-0">
        {enriched.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-[8px] font-mono text-slate-600">No data</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={enriched} margin={{ top: 4, right: 2, left: 0, bottom: 0 }}>
              <YAxis domain={["auto", "auto"]} hide dataKey="bodyLow" />
              <Tooltip content={<CandleTooltip currencySymbol={currencySymbol} />} />
              <Bar
                dataKey="bodyHeight"
                stackId="candle"
                isAnimationActive={true}
                animationDuration={600}
                shape={(props: any) => <CandleShape {...props} />}
              >
                {enriched.map((entry, idx) => (
                  <Cell key={idx} fill={entry.isBull ? colors.bull : colors.bear} />
                ))}
              </Bar>
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

/* ── main component ───────────────────────────────────────────────── */

export default function AssetIntelligence({ assetData }: { assetData: any }) {
  const [timeframe, setTimeframe] = useState("1M");
  const timeframes = ["1D", "5D", "15D", "1M", "ALL"];

  /* ---------- awaiting state ---------- */
  if (!assetData) {
    return (
      <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
              <CandlestickChart className="w-3.5 h-3.5 text-teal-400" />
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
  const rawData = timeframeData[timeframe] || allChartData;
  const data = enrichCandleData(rawData);

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

  const isAllView = timeframe === "ALL";

  /* ---------- Y-axis domain (padded) ---------- */
  const allLows = data.map((d: any) => d.low);
  const allHighs = data.map((d: any) => d.high);
  const minY = Math.min(...allLows);
  const maxY = Math.max(...allHighs);
  const yPad = (maxY - minY) * 0.08 || 1;

  return (
    <div className="w-full h-full rounded-2xl glass-card gradient-border p-5 flex flex-col group">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-teal-500/15 group-hover:border-teal-500/30">
            <CandlestickChart className="w-3.5 h-3.5 text-teal-400" />
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
          /* ALL view: 2×2 grid of mini candlestick charts */
          <div className="grid grid-cols-2 grid-rows-2 gap-2 p-2 h-full">
            {(["1D", "5D", "15D", "1M"] as const).map((tf) => (
              <MiniCandleChart
                key={tf}
                data={timeframeData[tf] || allChartData}
                colors={TIMEFRAME_COLORS[tf]}
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
            <ComposedChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 4 }}>
              <defs>
                <linearGradient id="gridFade" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(51, 65, 85, 0.12)" />
                  <stop offset="100%" stopColor="rgba(51, 65, 85, 0.03)" />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51, 65, 85, 0.12)"
                vertical={false}
              />
              <XAxis
                dataKey="time"
                tick={{ fill: "#475569", fontSize: 9, fontFamily: "var(--font-mono)" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[minY - yPad, maxY + yPad]}
                hide
                dataKey="bodyLow"
              />
              <Tooltip
                content={<CandleTooltip currencySymbol={currencySymbol} />}
                cursor={{
                  stroke: "rgba(45, 212, 191, 0.12)",
                  strokeWidth: 1,
                  strokeDasharray: "4 4",
                }}
              />
              {/* Invisible baseline bar to push candle bodies to correct Y position */}
              <Bar
                dataKey="bodyLow"
                stackId="candle"
                fill="transparent"
                isAnimationActive={false}
              />
              {/* Candlestick body + wick */}
              <Bar
                dataKey="bodyHeight"
                stackId="candle"
                isAnimationActive={true}
                animationDuration={1000}
                animationEasing="ease-out"
                shape={(props: any) => <CandleShape {...props} />}
              >
                {data.map((entry: any, idx: number) => (
                  <Cell
                    key={idx}
                    fill={entry.isBull ? BULL_COLOR : BEAR_COLOR}
                  />
                ))}
              </Bar>
            </ComposedChart>
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
