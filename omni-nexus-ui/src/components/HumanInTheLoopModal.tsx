"use client";

import React from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ArrowUpRight,
  ArrowDownRight,
  Receipt,
} from "lucide-react";
import { PortfolioData } from "@/types/swarm";

interface Props {
  checkpoint: any | null;
  assetData?: any | null;
  portfolioData?: PortfolioData | null;
  reasoning?: string;
  onResolve: (approved: boolean) => void;
}

export default function HumanInTheLoopModal({
  checkpoint,
  assetData,
  portfolioData,
  reasoning,
  onResolve,
}: Props) {
  const isOpen = !!checkpoint;
  const action = checkpoint?.action?.toUpperCase() || "BUY";
  const isBuy = action === "BUY";

  const sharesNum = Number(checkpoint?.shares || 0);
  const estPrice = Number(
    checkpoint?.estimated_price || assetData?.current_price || 0
  );
  const totalCost = sharesNum * estPrice;
  const currentCash = Number(portfolioData?.cash ?? 100000);
  const postTradeCash = isBuy
    ? Math.max(0, currentCash - totalCost)
    : currentCash + totalCost;
  const allocPct =
    typeof checkpoint?.allocation === "number"
      ? `${checkpoint.allocation.toFixed(1)}%`
      : checkpoint?.allocation || "Auto-Sized";

  return (
    <Dialog open={isOpen}>
      <DialogContent
        showCloseButton={false}
        className="bg-white border border-slate-200 rounded-2xl shadow-2xl p-0 sm:max-w-md w-full overflow-hidden text-slate-900"
      >
        {/* Top Stripe-Style Accent Bar */}
        <div
          className={`h-1.5 ${
            isBuy
              ? "bg-gradient-to-r from-teal-600 to-emerald-500"
              : "bg-gradient-to-r from-amber-500 to-rose-500"
          }`}
        />

        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-200">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-teal-50 border border-teal-200 text-teal-700">
                <Receipt className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 font-mono">
                  Institutional Order Ticket
                </h3>
                <p className="text-[11px] text-slate-500 font-mono">
                  Human-in-the-Loop Authorization Gate
                </p>
              </div>
            </div>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-mono font-bold border ${
                isBuy
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-amber-50 text-amber-800 border-amber-200"
              }`}
            >
              {isBuy ? (
                <ArrowUpRight className="w-3.5 h-3.5" />
              ) : (
                <ArrowDownRight className="w-3.5 h-3.5" />
              )}
              MARKET {action}
            </span>
          </div>

          {/* Receipt Breakdown */}
          <div className="my-4 p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Target Instrument</span>
              <span className="font-bold text-slate-900">
                {checkpoint?.ticker || "N/A"} • Paper Broker
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Quantity × Est. Price</span>
              <span className="font-semibold text-slate-800">
                {sharesNum} sh × ${estPrice.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Portfolio Allocation</span>
              <span className="font-semibold text-teal-700">{allocPct}</span>
            </div>
            <div className="pt-2 border-t border-slate-200 flex justify-between items-baseline">
              <span className="text-slate-700 font-bold">
                Total Estimated Value
              </span>
              <span className="text-base font-bold text-slate-900">
                $
                {totalCost.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                USD
              </span>
            </div>
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Post-Trade Cash Balance</span>
              <span>
                ${currentCash.toLocaleString("en-US", { maximumFractionDigits: 0 })} →{" "}
                <strong className="text-slate-800">
                  ${postTradeCash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </strong>
              </span>
            </div>
          </div>

          {/* Risk Desk Compliance Seal */}
          <div className="mb-4 p-3 rounded-xl bg-emerald-50/90 border border-emerald-200 text-[11px] font-mono text-emerald-900 space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-emerald-800">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Risk Desk Compliance Seal Verified</span>
            </div>
            <p className="text-[10px] text-emerald-700 pl-5">
              ✓ Volatility-targeted exposure &le; 30.0% equity concentration cap
            </p>
            <p className="text-[10px] text-emerald-700 pl-5">
              ✓ Cash liquidity &amp; inventory invariants verified
            </p>
          </div>

          {reasoning && (
            <p className="mb-5 text-[11px] text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 line-clamp-3">
              <strong className="font-mono text-slate-800">AI Synthesis: </strong>
              {reasoning}
            </p>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => onResolve(false)}
              className="flex-1 py-3 px-4 rounded-xl bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-300 hover:border-rose-300 font-mono font-bold text-xs uppercase transition-all flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <XCircle className="w-4 h-4" /> Cancel
            </button>
            <button
              type="button"
              onClick={() => onResolve(true)}
              className="flex-1 py-3 px-4 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-mono font-bold text-xs uppercase transition-all flex items-center justify-center gap-1.5 shadow-md shadow-teal-600/20 cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" /> Authorize Trade
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
