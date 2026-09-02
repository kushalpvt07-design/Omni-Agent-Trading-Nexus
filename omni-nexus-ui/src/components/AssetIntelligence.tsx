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

/**
 * Enrich data points with candlestick fields.
 *
 * Each point gets `_domainMin` embedded — the Y-axis domain minimum.
 * The custom bar shape uses this plus the bar's rendered y/height
 * (which maps to `high` → `_domainMin`) to derive pixelsPerUnit
 * and position open/close/low correctly.
 */
function enrichCandleData(data: any[], domainMin: number) {
  return data.map((d) => {
    const open = d.open ?? d.price;
    const close = d.close ?? d.price;
    const high = d.high ?? Math.max(open, close);
    const low = d.low ?? Math.min(open, close);
    const isBull = close >= open;

    return {
      ...d,
      open,
      close,
      high,
      low,
      isBull,
      _domainMin: domainMin,
    };
  });
}

/** Compute Y-axis domain with padding from raw OHLC data */
function computeDomain(data: any[]) {
  if (!data || data.length === 0) return { minY: 0, maxY: 0, yPad: 1, domainMin: 0 };
  const lows = data.map((d) => d.low ?? d.close ?? d.price ?? 0);
  const highs = data.map((d) => d.high ?? d.open ?? d.price ?? 0);
  const minY = Math.min(...lows);
  const maxY = Math.max(...highs);
  const yPad = (maxY - minY) * 0.08 || 1;
  return { minY, maxY, yPad, domainMin: minY - yPad };
}

/* ── custom candlestick bar shape ─────────────────────────────────── */

/**
 * Recharts renders a single Bar from the Y-axis domain minimum up to `high`.
 * Props received: x, y (pixel top = high), width, height (pixels from high to domainMin).
 *
 * We derive: pixelsPerUnit = height / (high - domainMin)
 * Then for any OHLC value V: pixelY = y + (high - V) * pixelsPerUnit
 */
function CandleShape(props: any) {
  const { x = 0, y: barY = 0, width = 0, height: barH = 0, payload } = props;
  if (!payload) return null;

  const { open, close, high, low, isBull, _domainMin } = payload;

  // Derive the pixel scale from what Recharts gave us
  const dataRange = high - _domainMin;
  if (dataRange <= 0 || barH <= 0) return null;
  const ppu = barH / dataRange; // pixels per unit of price

  // Convert data values to pixel Y
  const toY = (val: number) => barY + (high - val) * ppu;

  const bodyTopVal = Math.max(open, close);
  const bodyBotVal = Math.min(open, close);

  const wickTopY = toY(high);
  const wickBotY = toY(low);
  const bodyTopY = toY(bodyTopVal);
  const bodyBotY = toY(bodyBotVal);

  const bodyH = Math.max(bodyBotY - bodyTopY, 1);
  const wickH = Math.max(wickBotY - wickTopY, 0.5);

  const centerX = x + width / 2;
  const wickW = Math.max(1, width * 0.12);
  const bodyW = Math.max(2, width * 0.6);

  const fillColor = isBull ? BULL_COLOR : BEAR_COLOR;
  const fillColorDim = isBull ? BULL_COLOR_DIM : BEAR_COLOR_DIM;
  const isDoji = Math.abs(open - close) < 0.01;

  return (
    <g>
      {/* Wick (high→low shadow line) */}
      <rect
        x={centerX - wickW / 2}
        y={wickTopY}
        width={wickW}
        height={wickH}
        fill={isDoji ? DOJI_COLOR : fillColor}
        rx={0.5}
        opacity={0.7}
      />
      {/* Body (open→close) */}
      <rect
        x={centerX - bodyW / 2}
        y={bodyTopY}
        width={bodyW}
        height={bodyH}
        fill={isDoji ? DOJI_COLOR : isBull ? fillColorDim : fillColor}
        stroke={isDoji ? DOJI_COLOR : fillColor}
        strokeWidth={1}
        rx={1}
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

/* ── Reusable candlestick chart ──────────────────────────────────── */

function CandlestickChartInner({
  data,
  domainMin,
  domainMax,
  currencySymbol,
  showXAxis = true,
}: {
  data: any[];
  domainMin: number;
  domainMax: number;
  currencySymbol: string;
  showXAxis?: boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: showXAxis ? 4 : 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(51, 65, 85, 0.12)"
          vertical={false}
        />
        {showXAxis && (
          <XAxis
            dataKey="time"
            tick={{ fill: "#475569", fontSize: 9, fontFamily: "var(--font-mono)" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
        )}
        <YAxis
          domain={[domainMin, domainMax]}
          hide
        />
        <Tooltip
          content={<CandleTooltip currencySymbol={currencySymbol} />}
          cursor={{
            stroke: "rgba(45, 212, 191, 0.12)",
            strokeWidth: 1,
            strokeDasharray: "4 4",
          }}
        />
        {/* Single bar from domainMin to high — CandleShape draws
            the actual wick + body using the pixel scale it derives */}
        <Bar
          dataKey="high"
          isAnimationActive={false}
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
  );
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
  const { enriched, domainMin, domainMax } = useMemo(() => {
    const dom = computeDomain(data);
    return {
      enriched: enrichCandleData(data, dom.domainMin),
      domainMin: dom.domainMin,
      domainMax: dom.maxY + dom.yPad,
    };
  }, [data]);

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
          <CandlestickChartInner
            data={enriched}
            domainMin={domainMin}
            domainMax={domainMax}
            currencySymbol={currencySymbol}
            showXAxis={false}
          />
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

  /* ---------- Y-axis domain (padded) ---------- */
  const { minY, maxY, yPad, domainMin } = computeDomain(rawData);
  const domainMax = maxY + yPad;
  const data = enrichCandleData(rawData, domainMin);

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
          <CandlestickChartInner
            data={data}
            domainMin={domainMin}
            domainMax={domainMax}
            currencySymbol={currencySymbol}
            showXAxis={true}
          />
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
