"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Landmark,
  Coins,
  BarChart3,
  RefreshCw,
  Clock,
} from "lucide-react";
import {
  PortfolioData,
  PortfolioHistory,
  PortfolioHistoryPoint,
} from "@/types/swarm";

const TIMEFRAMES = ["1D", "1M", "1Y", "ALL"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

// Format currency with compact notation for Y-axis
function formatCompactCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(2)}k`;
  return `$${value.toFixed(2)}`;
}

// Format time label based on timeframe
function formatTimeLabel(timestamp: string, timeframe: Timeframe): string {
  const date = new Date(timestamp);
  switch (timeframe) {
    case "1D":
      return date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    case "1M":
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    case "1Y":
      return date.toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      });
    case "ALL":
      return date.toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      });
    default:
      return date.toLocaleDateString();
  }
}

// Custom tooltip for the chart
function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: PortfolioHistoryPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const date = new Date(point.timestamp);

  return (
    <div className="bg-[#0c1120]/95 backdrop-blur-xl border border-teal-500/20 rounded-xl px-3.5 py-2.5 shadow-2xl shadow-black/40">
      <p className="text-[10px] font-mono text-slate-400 mb-1">
        {date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })}{" "}
        {date.toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
          hour12: true,
        })}
      </p>
      <p className="text-sm font-bold font-mono text-slate-100">
        $
        {point.total_value.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </p>
    </div>
  );
}

export default function PortfolioLedger({
  portfolioData,
  token,
}: {
  portfolioData: PortfolioData | null;
  token?: string | null;
}) {
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>("1D");
  const [historyData, setHistoryData] = useState<PortfolioHistory | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch portfolio history for the selected timeframe
  const fetchHistory = useCallback(
    (timeframe: Timeframe) => {
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      fetch(
        `http://localhost:8000/api/v1/portfolio/history?timeframe=${timeframe}`,
        { headers }
      )
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data: PortfolioHistory) => {
          setHistoryData(data);
          setLastUpdated(new Date());
        })
        .catch(() => {});
    },
    [token]
  );

  // Fetch history when timeframe changes or portfolio updates
  useEffect(() => {
    fetchHistory(selectedTimeframe);
  }, [selectedTimeframe, fetchHistory, portfolioData?.total_value]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchHistory(selectedTimeframe);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  const handleTimeframeChange = (tf: Timeframe) => {
    setSelectedTimeframe(tf);
  };

  // Determine if portfolio is up or down
  const change = historyData?.change;
  const isPositive = change ? change.change_pct >= 0 : true;
  const chartColor = isPositive ? "#2dd4bf" : "#f43f5e";
  const chartGradientId = "portfolioGradient";

  // Prepare chart data with formatted labels
  const chartData = (historyData?.data_points || []).map((point) => ({
    ...point,
    label: formatTimeLabel(point.timestamp, selectedTimeframe),
  }));

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
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-10">
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
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/40 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center transition-all duration-300 group-hover:bg-violet-500/15">
            <Wallet className="w-3.5 h-3.5 text-violet-400" />
          </div>
          <h2 className="text-xs tracking-wider font-mono font-semibold text-slate-200 uppercase">
            Your Portfolio
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {/* Timeframe Selectors */}
          <div className="flex items-center gap-0.5 bg-[#030508]/60 rounded-lg border border-slate-800/30 p-0.5">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => handleTimeframeChange(tf)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-semibold tracking-wider transition-all duration-200 ${
                  selectedTimeframe === tf
                    ? "bg-teal-500/15 text-teal-400 border border-teal-500/25 shadow-sm shadow-teal-500/10"
                    : "text-slate-500 hover:text-slate-300 border border-transparent hover:bg-slate-800/30"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            className="w-7 h-7 rounded-lg bg-[#030508]/60 border border-slate-800/30 flex items-center justify-center text-slate-500 hover:text-teal-400 hover:border-teal-500/20 transition-all duration-200"
            title="Refresh portfolio data"
          >
            <RefreshCw
              className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`}
            />
          </button>
        </div>
      </div>

      {/* ── Total Value + Change ────────────────────────────── */}
      <div className="mb-4">
        <div className="flex items-baseline gap-3 mb-1">
          <span className="text-2xl md:text-3xl font-bold font-mono text-slate-100 tracking-tight stat-value">
            <span className="text-slate-400 text-lg mr-0.5">$</span>
            {total_value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>

          {change && (
            <div className="flex items-center gap-1.5">
              <span
                className={`flex items-center gap-0.5 text-sm font-bold font-mono ${
                  isPositive ? "text-teal-400" : "text-rose-400"
                }`}
              >
                {isPositive ? (
                  <TrendingUp className="w-3.5 h-3.5" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5" />
                )}
                {isPositive ? "+" : ""}
                {change.change_pct.toFixed(2)}%
              </span>
              <span
                className={`text-xs font-mono ${
                  isPositive ? "text-teal-500/60" : "text-rose-500/60"
                }`}
              >
                ({isPositive ? "+" : ""}$
                {Math.abs(change.change_amount).toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
                )
              </span>
            </div>
          )}
        </div>

        {/* Timestamp */}
        {lastUpdated && (
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-600">
            <Clock className="w-2.5 h-2.5" />
            {lastUpdated.toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
            })}
            ,{" "}
            {lastUpdated.toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
              second: "2-digit",
              hour12: true,
            })}{" "}
            {Intl.DateTimeFormat().resolvedOptions().timeZone
              .split("/")
              .pop()
              ?.replace("_", " ") || ""}
          </div>
        )}
      </div>

      {/* ── Portfolio Value Chart ───────────────────────────── */}
      <div className="mb-4 bg-[#020406]/40 rounded-xl border border-slate-800/20 p-2 pt-4 relative">
        {/* Gradient left accent line */}
        <div className="absolute left-0 top-0 bottom-0 w-[2px] rounded-full bg-gradient-to-b from-violet-500/40 via-teal-500/20 to-transparent" />

        {chartData.length >= 2 ? (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart
              data={chartData}
              margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id={chartGradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={chartColor} stopOpacity={0.25} />
                  <stop offset="50%" stopColor={chartColor} stopOpacity={0.08} />
                  <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 9, fill: "#475569", fontFamily: "monospace" }}
                interval="equidistantPreserveStart"
                minTickGap={40}
              />
              <YAxis
                domain={["dataMin - 50", "dataMax + 50"]}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 9, fill: "#475569", fontFamily: "monospace" }}
                tickFormatter={formatCompactCurrency}
                width={65}
              />
              <Tooltip
                content={<ChartTooltip />}
                cursor={{
                  stroke: "rgba(45, 212, 191, 0.15)",
                  strokeWidth: 1,
                  strokeDasharray: "4 4",
                }}
              />
              <Area
                type="monotone"
                dataKey="total_value"
                stroke={chartColor}
                strokeWidth={2}
                fill={`url(#${chartGradientId})`}
                animationDuration={800}
                animationEasing="ease-out"
                dot={false}
                activeDot={{
                  r: 4,
                  stroke: chartColor,
                  strokeWidth: 2,
                  fill: "#0a0e17",
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[180px] flex items-center justify-center">
            <div className="text-center">
              <div className="w-10 h-10 rounded-full border-2 border-slate-800/40 flex items-center justify-center mx-auto mb-2">
                <BarChart3 className="w-4 h-4 text-slate-700" />
              </div>
              <p className="text-slate-600 italic text-[11px] font-mono">
                Portfolio chart will appear as data accumulates
              </p>
              <p className="text-slate-700 text-[9px] font-mono mt-1">
                Value is recorded every 30 seconds
              </p>
            </div>
          </div>
        )}
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
            $
            {total_value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
        {/* Cash */}
        <div className="bg-[#030508]/60 rounded-xl border border-slate-800/30 p-2.5 text-center transition-all duration-300 hover:border-teal-500/15">
          <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
            <Coins className="w-2.5 h-2.5" />
            Cash
          </p>
          <p className="text-sm font-bold font-mono text-teal-400 tracking-wide">
            $
            {cash.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
        {/* Holdings */}
        <div className="bg-[#030508]/60 rounded-xl border border-slate-800/30 p-2.5 text-center transition-all duration-300 hover:border-cyan-500/15">
          <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-center gap-1">
            <BarChart3 className="w-2.5 h-2.5" />
            Holdings
          </p>
          <p className="text-sm font-bold font-mono text-cyan-400 tracking-wide">
            $
            {holdingsValue.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
        </div>
      </div>

      {/* ── Positions Table ────────────────────────────────── */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
          Positions
        </span>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-violet-400/80 bg-violet-950/20 px-2.5 py-1 rounded-lg border border-violet-500/15 transition-all duration-300 hover:border-violet-500/30">
          <BarChart3 className="w-3 h-3 text-violet-400" />
          <span>
            {positions.length} holding{positions.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-[80px] max-h-[180px] bg-[#020406]/60 rounded-xl border border-slate-800/30 overflow-y-auto custom-scrollbar relative">
        {/* Gradient left accent line */}
        <div className="absolute left-0 top-0 bottom-0 w-[2px] rounded-full bg-gradient-to-b from-violet-500/40 via-violet-500/10 to-transparent" />

        {!hasPositions ? (
          <div className="h-full flex items-center justify-center py-6">
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
                const posPositive = pos.current_price > 0;
                return (
                  <tr
                    key={pos.ticker}
                    className="border-b border-slate-800/20 transition-all duration-200 hover:bg-violet-500/[0.03] animate-fade-in-up"
                    style={{ animationDelay: `${index * 0.06}s` }}
                  >
                    <td className="py-1.5 px-3">
                      <div className="flex items-center gap-1.5">
                        {posPositive ? (
                          <TrendingUp className="w-2.5 h-2.5 text-teal-500/60" />
                        ) : (
                          <TrendingDown className="w-2.5 h-2.5 text-rose-500/60" />
                        )}
                        <span className="text-slate-200 font-semibold">
                          {pos.ticker}
                        </span>
                      </div>
                    </td>
                    <td className="py-1.5 px-3 text-right text-slate-400">
                      {pos.shares.toLocaleString("en-US", {
                        maximumFractionDigits: 4,
                      })}
                    </td>
                    <td className="py-1.5 px-3 text-right text-slate-400">
                      $
                      {pos.current_price.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td className="py-1.5 px-3 text-right">
                      <span
                        className={`font-semibold ${
                          pos.market_value > 0
                            ? "text-teal-400"
                            : "text-slate-500"
                        }`}
                      >
                        $
                        {pos.market_value.toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
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
