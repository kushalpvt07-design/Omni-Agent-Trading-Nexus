"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Zap,
  User,
  Lock,
  ArrowRight,
  AlertCircle,
  Eye,
  EyeOff,
  Shield,
  Activity,
} from "lucide-react";
import { isAuthenticated, loginUser, registerUser } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (isAuthenticated()) {
      router.replace("/");
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (mode === "login") {
        await loginUser(username, password);
      } else {
        await registerUser(username, password);
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setError("");
  };

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200 font-sans relative overflow-hidden flex items-center justify-center selection:bg-teal-500/30">
      {/* ── Animated Background ──────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a08_1px,transparent_1px),linear-gradient(to_bottom,#0f172a08_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div
          className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] rounded-full bg-teal-500/[0.04] blur-[120px]"
          style={{ animation: "orb-float-1 20s ease-in-out infinite" }}
        />
        <div
          className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] rounded-full bg-cyan-500/[0.04] blur-[100px]"
          style={{ animation: "orb-float-2 25s ease-in-out infinite" }}
        />
        <div
          className="absolute top-[30%] right-[40%] w-[400px] h-[400px] rounded-full bg-violet-500/[0.03] blur-[90px]"
          style={{ animation: "orb-float-1 30s ease-in-out infinite" }}
        />
        <div
          className="absolute w-full h-[1px] bg-gradient-to-r from-transparent via-teal-400/10 to-transparent"
          style={{ animation: "scan-line 8s linear infinite" }}
        />
      </div>

      {/* ── Login Card ───────────────────────────────────────── */}
      <div className="relative z-10 w-full max-w-md mx-4 animate-fade-in-up">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-teal-500/20 to-cyan-500/10 border border-teal-500/30 mb-4 relative group">
            <Zap className="w-7 h-7 text-teal-400" />
            <div className="absolute -inset-1 rounded-2xl bg-teal-400/10 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Omni-Agent Trading{" "}
            <span className="text-teal-400" style={{ textShadow: "0 0 20px rgba(45,212,191,0.3)" }}>
              Nexus
            </span>
          </h1>
          <p className="text-[11px] text-slate-500 font-mono mt-1.5 tracking-wider">
            Autonomous Swarm Financial Execution Engine
          </p>
        </div>

        {/* Glass Card */}
        <div className="relative">
          {/* Card glow effect */}
          <div className="absolute -inset-[1px] rounded-2xl bg-gradient-to-b from-teal-500/20 via-slate-700/20 to-violet-500/10 pointer-events-none" />
          <div className="relative rounded-2xl bg-[#0a0e1a]/80 backdrop-blur-xl border border-slate-800/40 p-8 shadow-2xl shadow-black/40">
            {/* Mode Toggle */}
            <div className="flex items-center bg-[#030508]/70 rounded-xl border border-slate-800/30 p-1 mb-7">
              <button
                onClick={() => { setMode("login"); setError(""); }}
                className={`flex-1 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider transition-all duration-300 ${
                  mode === "login"
                    ? "bg-teal-500/15 text-teal-400 border border-teal-500/25 shadow-sm shadow-teal-500/10"
                    : "text-slate-500 hover:text-slate-300 border border-transparent"
                }`}
              >
                SIGN IN
              </button>
              <button
                onClick={() => { setMode("register"); setError(""); }}
                className={`flex-1 py-2.5 rounded-lg text-xs font-mono font-semibold tracking-wider transition-all duration-300 ${
                  mode === "register"
                    ? "bg-violet-500/15 text-violet-400 border border-violet-500/25 shadow-sm shadow-violet-500/10"
                    : "text-slate-500 hover:text-slate-300 border border-transparent"
                }`}
              >
                SIGN UP
              </button>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="flex items-center gap-2 bg-rose-950/30 border border-rose-500/20 rounded-xl px-4 py-3 mb-5 animate-fade-in-up">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span className="text-xs text-rose-300 font-mono">{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Username */}
              <div className="group">
                <label className="block text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
                  Username
                </label>
                <div className="relative">
                  <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-teal-400 transition-colors duration-200">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    id="auth-username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    required
                    minLength={3}
                    maxLength={30}
                    pattern="^[a-zA-Z0-9_]+$"
                    autoComplete="username"
                    className="w-full pl-11 pr-4 py-3 rounded-xl bg-[#030508]/70 border border-slate-800/40 text-sm text-slate-200 font-mono placeholder:text-slate-700 focus:outline-none focus:border-teal-500/40 focus:ring-1 focus:ring-teal-500/20 transition-all duration-200 hover:border-slate-700/60"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="group">
                <label className="block text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-teal-400 transition-colors duration-200">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    id="auth-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === "register" ? "Min 6 characters" : "Enter password"}
                    required
                    minLength={6}
                    maxLength={128}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    className="w-full pl-11 pr-12 py-3 rounded-xl bg-[#030508]/70 border border-slate-800/40 text-sm text-slate-200 font-mono placeholder:text-slate-700 focus:outline-none focus:border-teal-500/40 focus:ring-1 focus:ring-teal-500/20 transition-all duration-200 hover:border-slate-700/60"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || !username || !password}
                className={`w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl text-sm font-mono font-bold tracking-wider transition-all duration-300 ${
                  isLoading
                    ? "bg-slate-800/50 text-slate-500 cursor-wait"
                    : mode === "login"
                    ? "bg-gradient-to-r from-teal-600/80 to-teal-500/70 text-white hover:from-teal-600 hover:to-teal-500 shadow-lg shadow-teal-500/10 hover:shadow-teal-500/20 active:scale-[0.98]"
                    : "bg-gradient-to-r from-violet-600/80 to-violet-500/70 text-white hover:from-violet-600 hover:to-violet-500 shadow-lg shadow-violet-500/10 hover:shadow-violet-500/20 active:scale-[0.98]"
                } disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>{mode === "login" ? "AUTHENTICATING..." : "CREATING ACCOUNT..."}</span>
                  </>
                ) : (
                  <>
                    <span>{mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-slate-800/40" />
              <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">
                {mode === "login" ? "New here?" : "Already have an account?"}
              </span>
              <div className="flex-1 h-px bg-slate-800/40" />
            </div>

            {/* Switch Mode Link */}
            <button
              onClick={toggleMode}
              className="w-full py-2.5 rounded-xl text-xs font-mono font-semibold text-slate-400 hover:text-teal-400 border border-slate-800/30 hover:border-teal-500/20 transition-all duration-200 hover:bg-teal-500/[0.03]"
            >
              {mode === "login" ? "Create a new account →" : "← Sign in to existing account"}
            </button>
          </div>
        </div>

        {/* Footer Info */}
        <div className="flex items-center justify-center gap-4 mt-6 text-[9px] font-mono text-slate-700">
          <span className="flex items-center gap-1">
            <Shield className="w-2.5 h-2.5" />
            PAPER TRADING MODE
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <Activity className="w-2.5 h-2.5" />
            $100,000 STARTING BALANCE
          </span>
        </div>
      </div>

      {/* ── Inline keyframe animation styles ─────────────────── */}
      <style jsx>{`
        @keyframes orb-float-1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -30px) scale(1.05); }
          66% { transform: translate(-20px, 20px) scale(0.95); }
        }
        @keyframes orb-float-2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-40px, 30px) scale(1.1); }
        }
        @keyframes scan-line {
          0% { top: -5%; }
          100% { top: 105%; }
        }
      `}</style>
    </div>
  );
}
