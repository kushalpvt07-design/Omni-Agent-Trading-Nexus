"use client";

import React from "react";
import { Dialog, DialogContent, DialogOverlay, DialogPortal } from "@/components/ui/dialog";
import { UserCheck, CheckCircle2, XCircle, ShieldAlert, ArrowUpRight, ArrowDownRight } from "lucide-react";

interface Props {
  checkpoint: any | null;
  onResolve: (approved: boolean) => void;
}

export default function HumanInTheLoopModal({ checkpoint, onResolve }: Props) {
  const isOpen = !!checkpoint;
  const isBuy = checkpoint?.action?.toUpperCase() === "BUY";

  return (
    <Dialog open={isOpen}>
      <DialogPortal>
        <DialogOverlay className="bg-slate-950/85 backdrop-blur-md z-50" />
        <DialogContent 
          showCloseButton={false} 
          className="bg-[#0a0f1a] border border-teal-500/20 rounded-2xl shadow-[0_0_60px_rgba(20,184,166,0.12)] p-0 max-w-md w-full overflow-hidden z-50"
        >
          {/* Top gradient accent */}
          <div className="h-1 bg-gradient-to-r from-teal-500 via-cyan-400 to-teal-500 animate-gradient-flow" />
          
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800/50">
              <div className="relative">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-teal-950/60 to-teal-900/20 border border-teal-500/25 text-teal-400 animate-data-pulse">
                  <ShieldAlert className="w-5 h-5" />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 font-mono tracking-wide">
                  Human-in-the-Loop
                </h3>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5">Authorization required to proceed</p>
              </div>
            </div>

            {/* Trade Details Grid */}
            <div className="grid grid-cols-4 gap-2 my-5 p-4 rounded-xl bg-[#030508]/80 border border-slate-800/40">
              <div className="text-center">
                <span className="text-[9px] text-slate-500 uppercase font-mono tracking-wider block mb-1.5">Ticker</span>
                <p className="text-sm font-bold text-slate-100 font-mono">{checkpoint?.ticker || "N/A"}</p>
              </div>
              <div className="text-center">
                <span className="text-[9px] text-slate-500 uppercase font-mono tracking-wider block mb-1.5">Action</span>
                <div className="flex items-center justify-center gap-1">
                  {isBuy ? (
                    <ArrowUpRight className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3 text-amber-400" />
                  )}
                  <p className={`text-sm font-bold ${isBuy ? "text-emerald-400" : "text-amber-400"}`}>
                    {checkpoint?.action || "REVIEW"}
                  </p>
                </div>
              </div>
              <div className="text-center">
                <span className="text-[9px] text-slate-500 uppercase font-mono tracking-wider block mb-1.5">Shares</span>
                <p className="text-sm font-bold text-slate-100 font-mono">{checkpoint?.shares || 0}</p>
              </div>
              <div className="text-center">
                <span className="text-[9px] text-slate-500 uppercase font-mono tracking-wider block mb-1.5">Alloc</span>
                <p className="text-sm font-bold text-teal-400 font-mono">
                  {typeof checkpoint?.allocation === 'number' ? `${checkpoint.allocation.toFixed(1)}%` : (checkpoint?.allocation || "N/A")}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => onResolve(true)}
                className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-slate-950 font-mono font-bold text-[11px] uppercase transition-all duration-300 flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(20,184,166,0.25)] hover:shadow-[0_0_30px_rgba(20,184,166,0.35)] cursor-pointer active:scale-[0.97]"
              >
                <CheckCircle2 className="w-4 h-4" /> Approve Trade
              </button>
              <button
                onClick={() => onResolve(false)}
                className="flex-1 py-3 px-4 rounded-xl bg-slate-900/60 hover:bg-slate-800/60 text-amber-400 border border-amber-500/20 hover:border-amber-500/35 font-mono font-bold text-[11px] uppercase transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer active:scale-[0.97]"
              >
                <XCircle className="w-4 h-4" /> Cancel
              </button>
            </div>
          </div>
        </DialogContent>
      </DialogPortal>
    </Dialog>
  );
}
