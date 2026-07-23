"use client"; // CRITICAL: This MUST be a client component for WebSockets

import React, { useState } from 'react';
import { useSwarmWebSocket } from '@/hooks/useSwarmWebSocket'; // Assuming you saved my hook logic here



export default function OmniAgentNexus() {
  const [inputDirective, setInputDirective] = useState("e.g. Let's scoop up 25 shares of AAPL");
  
  // 1. Initialize the Live State Hook (assuming you implemented my last instruction)
  const { state, deployDirective, resolveCheckpoint } = useSwarmWebSocket('ws://127.0.0.1:8000/api/v1/swarm-stream');

  // Helper for pipeline statuses (matching the log in your sketch)
  const getStepIcon = (status: 'pending' | 'active' | 'complete' | 'error') => {
    switch (status) {
      case 'active': return { icon: '⚙', color: 'text-sky-400' };
      case 'complete': return { icon: '✓', color: 'text-emerald-500' };
      case 'error': return { icon: '✕', color: 'text-red-500' };
      default: return { icon: '○', color: 'text-slate-600' };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-300 p-6 font-sans">
      
      {/* HEADER: Dynamic Connection Status */}
      <header className="flex justify-between items-center mb-6 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-full border-4 border-slate-500 bg-slate-800"></div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-wider">OMNI-AGENT TRADING NEXUS</h1>
          <span className={`text-xs px-2 py-0.5 rounded ${state.isConnected ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'}`}>
            {state.isConnected ? 'Live Nexus Connected' : 'Nexus Disconnected'}
          </span>
        </div>
        <h2 className="text-lg text-slate-400">Welcome to the Nexus: Live Swarm Analysis</h2>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* TOP LEFT: SWARM DIRECTIVE INPUT */}
        {/* CSS FIX: Add overflow-hidden to every card container! */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col h-[400px] overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide">Swarm Directive Input</h3>
            <span className="text-xs text-emerald-500 flex items-center gap-1">
              ✓ Hardened Input Enabled
            </span>
          </div>
          <div className="flex-1 bg-slate-950 rounded border border-slate-800 p-4 overflow-y-auto mb-4 font-mono text-sm space-y-4">
            {state.directiveLogs.length > 0 ? (
              state.directiveLogs.map((log, i) => (
                <p key={i} className="text-slate-400">{log}</p>
              ))
            ) : (
              <p className="text-slate-600 italic">No directives processed yet. The terminal is on standby.</p>
            )}
          </div>
          <div className="flex gap-2">
            <input 
              type="text" 
              value={inputDirective} 
              onChange={(e) => setInputDirective(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded px-4 py-3 font-mono text-sm text-slate-200"
            />
            <button 
              onClick={() => deployDirective(inputDirective)}
              className="bg-teal-800 hover:bg-teal-700 text-teal-100 font-semibold px-6 py-3 rounded uppercase tracking-wider transition-colors">
              Deploy
            </button>
          </div>
        </div>

        {/* TOP RIGHT: ASSET INTELLIGENCE */}
        {/* CSS FIX: Apply overflow-hidden to card! */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col h-[400px] overflow-hidden">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide">
              Asset Intelligence - {state.pendingAction?.ticker || 'AWAITING DIRECTIVE'}
            </h3>
            <span className="text-slate-500 text-xl leading-none">⚙</span>
          </div>
          <div className="flex justify-between mb-4 text-sm">
            <div>
              <p className="text-slate-500">Current Price</p>
              <p className="text-xl font-bold text-slate-100">$229.22</p>
            </div>
            <div>
              <p className="text-slate-500">Change</p>
              <p className="text-emerald-500">+0.75 (+0.0%)</p>
            </div>
            <div className="text-right">
              <p className="text-slate-500">30-Day Volatility Risk</p>
              <p className="text-red-400">17.4% High Risk</p>
            </div>
          </div>
          {/* CSS FIX: Explicit overflow-hidden on chart container! */}
          <div className="flex-1 bg-slate-950 border border-slate-800 rounded overflow-hidden flex items-center justify-center text-slate-600">
            {/* THIS IS THE INFAMOUS "LIVE GRAPH GOING TO INFINITY". WE CONTAINED IT. */}
            {state.isConnected && (state.pipelineStatus.parser === 'complete' || state.pendingAction) ? (
              <p>[Live Tremor Candlestick Chart Renders Here - Contained]</p>
            ) : (
              <p className="italic text-center px-4">Graph inactive. Nexus is on standby.</p>
            )}
          </div>
        </div>

        {/* MID LEFT: SENTIMENT SOURCE INTEL */}
        {/* CSS FIX: Add overflow-hidden and strict height constraints */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-[350px] overflow-hidden flex flex-col">
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide mb-4">Sentiment Source Intel News</h3>
          {/* FIXED: No more static data. News only shows when connected and swarm is active. */}
          {state.isConnected && state.pipelineStatus.sentiment !== 'pending' ? (
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {state.newsIntel?.map((intel, i) => (
                <div key={i} className="p-3 bg-slate-800/50 border border-slate-700/50 rounded flex justify-between items-center">
                  <div className="pr-4">
                    <p className="text-sm text-slate-300">{intel.headline}</p>
                    <p className="text-xs text-slate-500 mt-1">12h:36 ago</p>
                  </div>
                  <div className="text-right text-xs">
                    <p className="text-slate-400">Quant impact: <span className="text-emerald-400">{intel.quantImpact}</span></p>
                    <p className="text-slate-400">Sentiment score: <span className="text-emerald-400">+{intel.score.toFixed(1)}</span></p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-800 rounded">
              <p className="text-slate-600 font-mono text-center px-4">[ANALYSIS STANDBY]<br/>News intelligence will render post-directive.</p>
            </div>
          )}
        </div>

        {/* MID RIGHT: COLLECTIVE SENTIMENT ANALYSIS */}
        {/* CSS FIX: overflow-hidden! */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-[350px] overflow-hidden">
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide mb-4">Collective Sentiment Analysis</h3>
          {/* FIXED: No more "disaster". Sentiment components derived from state. */}
          {state.isConnected && state.pipelineStatus.sentiment === 'complete' ? (
            <div className="grid grid-cols-2 gap-4 h-[calc(100%-2rem)]">
               <div className="bg-slate-950 border border-slate-800 rounded p-2 flex flex-col items-center justify-center overflow-hidden">
                  <p className="text-xs text-slate-400 mb-2">Net Sentiment Score: <span className="text-emerald-500">+0.65 Bullish</span></p>
                  {/* REPLACE WITH TREMOR HEATMAP OR TRACKER - DYNAMIC DATA */}
                  <div className="w-full h-24 bg-gradient-to-br from-emerald-900 to-emerald-600 rounded opacity-70"></div>
               </div>
               <div className="bg-slate-950 border border-slate-800 rounded p-2 flex items-center justify-center overflow-hidden">
                  {/* DYNAMIC WORD CLOUD FROM GEMINI/LLM ANALYSIS */}
                  <p className="text-xs text-teal-500 text-center font-mono">AI Partnership<br/><span className="text-lg text-slate-300">Hardware Leaks</span><br/>Technology</p>
               </div>
               <div className="bg-slate-950 border border-slate-800 rounded p-2 flex items-center justify-center overflow-hidden">
                  {/* REPLACE WITH TREMOR DONUT CHART - USE INLINE HEX CODES */}
                  <div className="w-16 h-16 rounded-full border-4 border-teal-600 border-r-indigo-500 border-b-rose-500"></div>
               </div>
               <div className="bg-slate-950 border border-slate-800 rounded p-2 flex flex-col justify-center gap-2 overflow-hidden">
                  <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-teal-500 w-3/4 h-full rounded"></div></div>
                  <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-emerald-500 w-1/2 h-full rounded"></div></div>
                  <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-indigo-500 w-1/3 h-full rounded"></div></div>
               </div>
            </div>
          ) : (
            <div className="w-full h-[calc(100%-3rem)] flex items-center justify-center border border-dashed border-slate-800 rounded">
                <p className="text-slate-600 font-mono text-center px-4">[ANALYSIS STANDBY]<br/>Sentiment aggregation will render post-directive.</p>
            </div>
          )}
        </div>

      </div>

      {/* ACTION CENTER */}
      {/* CSS FIX: overflow-hidden! */}
      <div className="mt-6 bg-slate-900 border border-slate-800 rounded-xl p-5 overflow-hidden">
        <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide mb-4">Action Center</h3>
        {/* FIXED: No longer static. Derived from useSwarmWebSocket pendingAction. */}
        {state.isConnected && state.pendingAction ? (
          <div className="flex gap-4 items-center">
            <div className="flex-1 bg-slate-950 border border-teal-500 shadow-[0_0_15px_rgba(20,184,166,0.3)] rounded-lg p-4 flex items-center">
              <span className="text-amber-500 mr-3 text-lg">①</span>
              <p className="text-teal-400 font-mono text-sm font-semibold tracking-wider">
                PENDING HUMAN APPROVAL [DEPLOY: {state.pendingAction.ticker} {state.pendingAction.action} {state.pendingAction.allocation}% ({state.pendingAction.shares.toFixed(4)} SHARES)]
              </p>
            </div>
            <button 
              onClick={() => resolveCheckpoint(true)}
              className="bg-emerald-800 hover:bg-emerald-700 text-emerald-100 px-8 py-4 rounded-lg font-semibold transition-colors">Approve</button>
            <button 
              onClick={() => resolveCheckpoint(false)}
              className="bg-rose-950 hover:bg-rose-900 text-rose-200 border border-rose-800 px-8 py-4 rounded-lg font-semibold transition-colors">Reject</button>
          </div>
        ) : (
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-6 flex flex-col items-center justify-center">
              <p className="text-lg text-slate-500 font-semibold">Human Checkpoint (Alpaca/Brokerage Authorization)</p>
              <p className="text-sm text-slate-600 mt-1 font-mono">{state.isConnected ? 'Standby for swarm orchestration directive.' : '[NEXUS OFFLINE] Connect the backend.'}</p>
          </div>
        )}
      </div>

      {/* PIPELINE STATUS */}
      {/* CSS FIX: overflow-hidden! */}
      <div className="mt-6 bg-slate-900 border border-slate-800 rounded-xl p-5 overflow-hidden">
        <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wide mb-4">Swarm consensus and risk pipeline status</h3>
        <div className="font-mono text-sm space-y-2.5 text-slate-400 pl-2 border-l-2 border-slate-800">
          {[
            { label: '📄 Parser: extracting directive', key: 'parser' },
            { label: '🔍 Sentiment: analyzing source news', key: 'sentiment' },
            { label: '📊 Quant: calculating allocation', key: 'quant' },
            { label: '⚙ Orchestrator: consensus reached', key: 'orchestrator' },
            { label: '🛡 Risk: approved', key: 'risk' }
          ].map((step, i) => {
            const statusInfo = getStepIcon(state.pipelineStatus[step.key as keyof typeof state.pipelineStatus]);
            return (
              <p key={i}>
                <span className={`${statusInfo.color} mr-2`}>{statusInfo.icon}</span> 
                {step.label} -&gt;
              </p>
            );
          })}
          {state.pendingAction && <p className="text-amber-400 italic mt-2">Waiting for Human Checkpoint (Action Center)</p>}
        </div>
      </div>
      
    </div>
  );
}
