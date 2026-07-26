"use client";

import React from "react";
import { Dialog, DialogContent, DialogOverlay, DialogPortal } from "@/components/ui/dialog";
import { UserCheck, CheckCircle2, XCircle } from "lucide-react";

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
        <DialogOverlay className="bg-slate-950/80 backdrop-blur-sm z-50" />
        <DialogContent 
          showCloseButton={false} 
          className="bg-[#0C121C] border border-teal-500/30 rounded-2xl shadow-[0_0_40px_rgba(20,184,166,0.15)] p-6 max-w-md w-full"
        >
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-teal-500 via-cyan-400 to-teal-500" />
          
          <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
            <div className="p-2 rounded-lg bg-teal-950/40 border border-teal-500/30 text-teal-400">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 font-mono tracking-wide">
                Human-in-the-Loop: Pending Authorization
              </h3>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 my-5 p-4 rounded-xl bg-[#05080F] border border-slate-800/80 text-center font-mono">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Ticker</span>
              <p className="text-sm font-bold text-slate-100 mt-1">{checkpoint?.ticker || "N/A"}</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Action</span>
              <p className={`text-sm font-bold mt-1 ${isBuy ? "text-emerald-400" : "text-amber-400"}`}>
                {checkpoint?.action || "REVIEW"}
              </p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Shares</span>
              <p className="text-sm font-bold text-slate-100 mt-1">{checkpoint?.shares || 0}</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Alloc</span>
              <p className="text-sm font-bold text-teal-400 mt-1">
                {typeof checkpoint?.allocation === 'number' ? `${checkpoint.allocation.toFixed(1)}%` : (checkpoint?.allocation || "N/A")}
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => onResolve(true)}
              className="flex-1 py-2.5 px-4 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-mono font-bold text-[11px] uppercase transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(20,184,166,0.3)] cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" /> Approve Trade
            </button>
            <button
              onClick={() => onResolve(false)}
              className="flex-1 py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-amber-400 border border-amber-500/30 font-mono font-bold text-[11px] uppercase transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <XCircle className="w-4 h-4" /> Cancel
            </button>
          </div>
        </DialogContent>
      </DialogPortal>
    </Dialog>
  );
}
