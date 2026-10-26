"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Clock,
  History,
  PieChart as PieChartIcon,
  Layers,
} from "lucide-react";
import {
  PortfolioData,
  PortfolioHistory,
  PortfolioHistoryPoint,
  TradeRecord,
} from "@/types/swarm";

const TIMEFRAMES = ["1D", "1M", "1Y", "ALL"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const DONUT_COLORS = ["#0D9488", "#4F46E5", "#10B981", "#F59E0B", "#EC4899", "#6366F1", "#94A3B8"];

function formatCompactCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
}

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
    default:
      return date.toLocaleDateString("en-US", {
        month: "short",
        year: "2-digit",
      });
  }
}

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
    <div className="bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl px-3.5 py-2 shadow-lg">
      <p className="text-[10px] font-mono text-slate-500 mb-0.5">
        {date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        })}{" "}
        {date.toLocaleTimeString("en-US", {
          hour: "numeric",
          minute: "2-digit",
        })}
      </p>
      <p className="text-sm font-bold font-mono text-slate-900">
        $
        {Number(point.total_value ?? 0).toLocaleString("en-US", {
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
  const [activeTab, setActiveTab] = useState<"holdings" | "trades" | "allocation">("holdings");
  const [historyData, setHistoryData] = useState<PortfolioHistory | null>(null);
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHistoryAndTrades = useCallback(
    (timeframe: Timeframe) => {
      if (!token) return;
      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
      };

      fetch(
        `http://localhost:8000/api/v1/portfolio/history?timeframe=${timeframe}`,
        { headers }
      )
        .then((res) => (res.ok ? res.json() : null))
        .then((data: PortfolioHistory | null) => {
          if (data) {
            setHistoryData(data);
            setLastUpdated(new Date());
          }
        })
        .catch(() => {});

      fetch(`http://localhost:8000/api/v1/portfolio/trades?limit=30`, { headers })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data?.trades) setTrades(data.trades);
        })
        .catch(() => {});
    },
    [token]
  );

  useEffect(() => {
    fetchHistoryAndTrades(selectedTimeframe);
  }, [selectedTimeframe, fetchHistoryAndTrades, portfolioData?.total_value]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchHistoryAndTrades(selectedTimeframe);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  if (!portfolioData) {
    return (
      <div className="w-full rounded-2xl bento-card p-5 flex flex-col">
        <div className="flex items-center gap-2.5 pb-3 border-b border-slate-200">
          <Wallet className="w-4 h-4 text-teal-600" />
          <h2 className="text-xs font-mono font-bold uppercase text-slate-800">
            Portfolio &amp; Trade Audit Ledger
          </h2>
        </div>
        <div className="py-12 text-center text-xs font-mono text-slate-400">
          Loading portfolio ledger...
        </div>
      </div>
    );
  }

  const cash = Number(portfolioData.cash ?? 0);
  const positions = Array.isArray(portfolioData.positions) ? portfolioData.positions : [];
  const total_value = Number(portfolioData.total_value ?? cash);
  const holdingsValue = Math.max(0, total_value - cash);

  const change = historyData?.change;
  const isPositive = change ? change.change_pct >= 0 : true;
  const chartColor = isPositive ? "#059669" : "#E11D48";

  const chartData = (historyData?.data_points || []).map((point) => ({
    ...point,
    label: formatTimeLabel(point.timestamp, selectedTimeframe),
  }));

  const donutData = [
    ...positions.map((p) => ({ name: p.ticker, value: p.market_value })),
    { name: "Cash (USD)", value: cash },
  ];

  return (
    <div className="w-full rounded-2xl bento-card p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/80 mb-3.5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center">
            <Wallet className="w-3.5 h-3.5 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-xs tracking-wider font-mono font-bold text-slate-900 uppercase">
              Portfolio &amp; Trade Audit
            </h2>
            {lastUpdated && (
              <p className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                Updated {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <div className="flex bg-slate-100 rounded-lg border border-slate-200 p-0.5">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-2 py-1 rounded-md text-[10px] font-mono font-semibold transition-all cursor-pointer ${
                  selectedTimeframe === tf
                    ? "bg-white text-teal-700 shadow-2xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="w-7 h-7 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 hover:text-teal-700 cursor-pointer"
            title="Refresh portfolio"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Total Equity + 3 KPI Pills */}
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <div>
          <span className="text-2xl font-bold font-mono text-slate-900">
            $
            {total_value.toLocaleString("en-US", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
          {change && (
            <span
              className={`ml-2 inline-flex items-center gap-0.5 text-xs font-bold font-mono px-2 py-0.5 rounded-full border ${
                isPositive
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-rose-50 text-rose-700 border-rose-200"
              }`}
            >
              {isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              {isPositive ? "+" : ""}
              {change.change_pct.toFixed(2)}%
            </span>
          )}
        </div>

        <div className="flex gap-3 text-xs font-mono">
          <span className="text-slate-500">
            Cash:{" "}
            <strong className="text-teal-700">
              ${cash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </strong>
          </span>
          <span className="text-slate-500">
            Holdings:{" "}
            <strong className="text-indigo-700">
              ${holdingsValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </strong>
          </span>
        </div>
      </div>

      {/* Step-Area Equity Curve Chart */}
      <div className="h-[135px] w-full bg-slate-50/70 rounded-xl border border-slate-200/70 p-2 mb-3.5">
        {chartData.length >= 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={
                chartData.length === 1
                  ? [chartData[0], { ...chartData[0], label: "" }]
                  : chartData
              }
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="portfolioDaylightGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={chartColor} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={chartColor} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 9, fill: "#64748B", fontFamily: "monospace" }}
                minTickGap={40}
              />
              <YAxis
                domain={["dataMin - 50", "dataMax + 50"]}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 9, fill: "#64748B", fontFamily: "monospace" }}
                tickFormatter={formatCompactCurrency}
                width={55}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="stepAfter"
                dataKey="total_value"
                stroke={chartColor}
                strokeWidth={2}
                fill="url(#portfolioDaylightGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs font-mono text-slate-400">
            Recording equity curve snapshots...
          </div>
        )}
      </div>

      {/* 3-Tab Switcher: Holdings | Trade History | Allocation Donut */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200 mb-3">
        <button
          type="button"
          onClick={() => setActiveTab("holdings")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-mono font-semibold transition-all cursor-pointer ${
            activeTab === "holdings"
              ? "bg-white text-slate-900 shadow-2xs"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-teal-600" />
          <span>Holdings ({positions.length})</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("trades")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-mono font-semibold transition-all cursor-pointer ${
            activeTab === "trades"
              ? "bg-white text-slate-900 shadow-2xs"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <History className="w-3.5 h-3.5 text-indigo-600" />
          <span>Trade Log ({trades.length})</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("allocation")}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-mono font-semibold transition-all cursor-pointer ${
            activeTab === "allocation"
              ? "bg-white text-slate-900 shadow-2xs"
              : "text-slate-500 hover:text-slate-800"
          }`}
        >
          <PieChartIcon className="w-3.5 h-3.5 text-emerald-600" />
          <span>Allocation</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="h-[190px] bg-slate-50/80 rounded-xl border border-slate-200/80 overflow-y-auto custom-scrollbar">
        {activeTab === "holdings" && (
          positions.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs font-mono text-slate-400">
              No open positions in ledger
            </div>
          ) : (
            <table className="w-full text-[11px] font-mono">
              <thead className="sticky top-0 bg-slate-100/95 border-b border-slate-200 text-slate-500 uppercase">
                <tr>
                  <th className="text-left py-2 px-3">Ticker</th>
                  <th className="text-right py-2 px-2">Qty</th>
                  <th className="text-right py-2 px-2">Price</th>
                  <th className="text-right py-2 px-2">Value</th>
                  <th className="text-right py-2 px-3">Unrealized P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const costBasis = pos.shares * (pos.avg_cost || pos.current_price);
                  const pnlDollar = pos.market_value - costBasis;
                  const pnlPct =
                    pos.avg_cost > 0
                      ? ((pos.current_price - pos.avg_cost) / pos.avg_cost) * 100
                      : 0;
                  const isUp = pnlDollar >= -0.01;

                  return (
                    <tr
                      key={pos.ticker}
                      className="border-b border-slate-200/60 bg-white hover:bg-slate-50/90"
                    >
                      <td className="py-2 px-3 font-bold text-slate-900">
                        {pos.ticker}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-600">
                        {Number(pos.shares).toLocaleString("en-US", {
                          maximumFractionDigits: 3,
                        })}
                      </td>
                      <td className="py-2 px-2 text-right text-slate-700">
                        ${Number(pos.current_price).toFixed(2)}
                      </td>
                      <td className="py-2 px-2 text-right font-semibold text-slate-900">
                        ${Number(pos.market_value).toLocaleString("en-US", {
                          minimumFractionDigits: 2,
                        })}
                      </td>
                      <td className="py-2 px-3 text-right">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                            isUp
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-rose-50 text-rose-700 border-rose-200"
                          }`}
                        >
                          {isUp ? "+" : ""}
                          {pnlPct.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )
        )}

        {activeTab === "trades" && (
          trades.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs font-mono text-slate-400">
              No executed trades yet
            </div>
          ) : (
            <div className="divide-y divide-slate-200/70">
              {trades.map((t, idx) => (
                <div key={idx} className="p-2.5 bg-white hover:bg-slate-50 flex items-center justify-between text-[11px] font-mono">
                  <div>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold mr-2 border ${
                        t.action === "BUY"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-rose-50 text-rose-700 border-rose-200"
                      }`}
                    >
                      {t.action}
                    </span>
                    <strong className="text-slate-900">{t.ticker}</strong>
                    <span className="text-slate-500 ml-1.5">
                      {Number(t.shares).toFixed(2)} sh @ ${Number(t.price).toFixed(2)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-slate-900">
                      ${Number(t.total_value).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                    <p className="text-[9px] text-slate-400">
                      {t.created_at ? new Date(t.created_at).toLocaleDateString() : ""}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {activeTab === "allocation" && (
          <div className="h-full flex items-center justify-between px-4 py-2 bg-white">
            <div className="w-1/2 h-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={donutData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={38}
                    outerRadius={62}
                    paddingAngle={2}
                  >
                    {donutData.map((_, i) => (
                      <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="w-1/2 space-y-1.5 font-mono text-[10px]">
              <p className="text-slate-500 font-semibold uppercase">
                Risk Desk Cap: 30.0% / Asset
              </p>
              {donutData.slice(0, 5).map((item, i) => {
                const pct = total_value > 0 ? (item.value / total_value) * 100 : 0;
                return (
                  <div key={item.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-slate-700">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: DONUT_COLORS[i % DONUT_COLORS.length] }}
                      />
                      {item.name}
                    </span>
                    <span className="font-bold text-slate-900">{pct.toFixed(1)}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
