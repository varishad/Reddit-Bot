'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import {
  CheckCircle2, XCircle, AlertTriangle, Wifi, Clock, Zap, RefreshCw, Globe, Power
} from 'lucide-react';
import { PowerButton } from '@/components/PowerButton';
import { StatCard } from '@/components/StatCard';
import { LogViewer } from '@/components/LogViewer';
import { botApi, BotStatus, LogEntry } from '@/lib/api';

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600).toString().padStart(2, '0');
  const m = Math.floor((secs % 3600) / 60).toString().padStart(2, '0');
  const s = (secs % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

export default function DashboardPage() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [actionLoading, setActionLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const { data } = await botApi.status();
      setStatus(data);
      setLogs(data.recent_logs ?? []);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  // Poll every 2 seconds
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  const handleToggle = async () => {
    setActionLoading(true);
    try {
      if (status?.is_running) {
        await botApi.stop();
      } else {
        await botApi.start('credentials.txt', 1);
      }
      await refresh();
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const stats = status?.stats;
  const isRunning = status?.is_running ?? false;
  const successRate = stats && stats.total > 0
    ? Math.round((stats.success / stats.total) * 100)
    : 0;

  return (
    <div className="min-h-screen relative">
      {/* Backend offline banner - floating style in main dashboard area */}
      <AnimatePresence>
        {backendOnline === false && (
          <motion.div
            initial={{ y: -40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -40, opacity: 0 }}
            className="absolute top-3 left-0 right-0 z-50 mx-4 bg-rose-600/95 text-white text-xs text-center py-2.5 font-semibold rounded-xl shadow-lg backdrop-blur border border-rose-500/30"
          >
            ⚠️ Backend Offline — Run <code className="mx-1 bg-white/20 px-1.5 py-0.5 rounded">python3 server.py</code> to connect
          </motion.div>
        )}
      </AnimatePresence>

      <div className={clsx(
        "flex flex-col gap-6 p-6 lg:p-8",
        backendOnline === false && "pt-14"
      )}>
        {/* Unified Status Header */}
        <header className="flex flex-wrap items-center justify-between gap-4 bg-white/[0.03] p-4 px-5 rounded-[20px] border border-white/[0.05] backdrop-blur-md shadow-xl">
          <div className="flex flex-wrap items-center gap-4 lg:gap-5">
            {/* Session Indicator */}
            <div className="flex flex-col gap-1">
              <span className="text-[9px] uppercase tracking-[0.15em] text-slate-500 font-extrabold">Active Session</span>
              <div className="px-3 py-1.5 bg-white/[0.03] rounded-lg border border-white/[0.05]">
                <span className="text-[11px] text-slate-300 font-mono font-medium">
                  {status?.session_id ? status.session_id.slice(0, 16) : 'READY TO START'}
                </span>
              </div>
            </div>

            <div className="h-10 w-px bg-white/10 hidden md:block" />

            {/* VPN Status */}
            <div className="flex flex-col gap-1">
              <span className="text-[9px] uppercase tracking-[0.15em] text-slate-500 font-extrabold">Network Layer</span>
              <div className={clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all duration-500',
                status?.vpn_location && status.vpn_location !== 'Disconnected'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              )}>
                <Globe className="w-4 h-4" />
                {status?.vpn_location || 'Disconnected'}
              </div>
            </div>

            <div className="h-10 w-px bg-white/10 hidden md:block" />

            {/* Browser Status */}
            <div className="flex flex-col gap-1">
              <span className="text-[9px] uppercase tracking-[0.15em] text-slate-500 font-extrabold">Engine State</span>
              <div className={clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all duration-500',
                isRunning
                  ? 'bg-blue-500/10 border-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                  : 'bg-white/[0.03] border-white/[0.05] text-slate-500'
              )}>
                <Zap className="w-4 h-4" />
                {status?.browser_status || (isRunning ? 'Initializing...' : 'Idle')}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              className="group flex items-center gap-2 px-3 py-2 lg:px-4 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] transition-all text-slate-300 hover:text-white border border-white/[0.05] active:scale-95"
            >
              <RefreshCw className={clsx("w-4 h-4 transition-transform duration-500 group-hover:rotate-180", actionLoading && "animate-spin")} />
              <span className="text-[11px] font-bold uppercase tracking-wider hidden lg:inline">Sync</span>
            </button>
          </div>
        </header>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
          {/* Left Column: Activity & Stats */}
          <div className="lg:col-span-8 flex flex-col gap-6 lg:gap-8">
            {/* Live Activity Section */}
            <section className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-1.5 h-4 bg-accent rounded-full" />
                  <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Live Activity Feed</h3>
                </div>
                {isRunning && (
                  <div className="flex items-center gap-2 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 backdrop-blur-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    LIVE PROCESSING
                  </div>
                )}
              </div>
              <div className="glass rounded-[24px] overflow-hidden border-white/[0.06] shadow-2xl">
                <LogViewer logs={logs} />
              </div>
            </section>

            {/* Performance Metrics Stats */}
            <section className="flex flex-col gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-1.5 h-4 bg-blue-500 rounded-full" />
                <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Performance Metrics</h3>
              </div>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard
                  label="Scanned"
                  value={stats?.total ?? 0}
                  icon={<Zap className="w-4 h-4" />}
                  color="blue"
                />
                <StatCard
                  label="Success"
                  value={`${successRate}%`}
                  icon={<CheckCircle2 className="w-4 h-4" />}
                  color="green"
                />
                <StatCard
                  label="Invalid"
                  value={stats?.invalid ?? 0}
                  icon={<XCircle className="w-4 h-4" />}
                  color="red"
                />
                <StatCard
                  label="Shielded"
                  value={stats?.banned ?? 0}
                  icon={<AlertTriangle className="w-4 h-4" />}
                  color="yellow"
                />
              </div>
            </section>
          </div>

          {/* Right Column: Controls & Hardware */}
          <aside className="lg:col-span-4 flex flex-col gap-6 lg:gap-8 sticky top-8">
            {/* Control Center */}
            <div className="flex flex-col gap-6 p-6 bg-white/[0.03] rounded-[28px] border border-white/[0.05] backdrop-blur-sm shadow-xl relative overflow-hidden group">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-1.5 h-4 bg-accent rounded-full" />
                  <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400">Control Center</h3>
                </div>
                <div className={clsx(
                  "px-3 py-1 rounded-full text-[9px] font-black tracking-widest border transition-all duration-500",
                  isRunning
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                    : "bg-white/5 border-white/10 text-slate-500"
                )}>
                  {isRunning ? "RUNNING" : "STANDBY"}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={handleToggle}
                  disabled={actionLoading || isRunning}
                  className={clsx(
                    "flex flex-col items-center justify-center gap-2 py-5 rounded-2xl border transition-all duration-300",
                    !isRunning
                      ? "bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20 text-emerald-400 active:scale-95"
                      : "bg-white/5 border-white/5 text-slate-600 grayscale cursor-not-allowed"
                  )}
                >
                  <Power className="w-6 h-6" />
                  <span className="text-[10px] font-black uppercase tracking-widest">Start Bot</span>
                </button>

                <button
                  onClick={handleToggle}
                  disabled={actionLoading || !isRunning}
                  className={clsx(
                    "flex flex-col items-center justify-center gap-2 py-5 rounded-2xl border transition-all duration-300",
                    isRunning
                      ? "bg-rose-500/10 hover:bg-rose-500/20 border-rose-500/20 text-rose-400 active:scale-95"
                      : "bg-white/5 border-white/5 text-slate-600 grayscale cursor-not-allowed"
                  )}
                >
                  <Power className="w-6 h-6 rotate-180" />
                  <span className="text-[10px] font-black uppercase tracking-widest">Stop Bot</span>
                </button>
              </div>

              <div className="flex items-center justify-between px-2 pt-2 border-t border-white/[0.05]">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span className="text-[10px] font-mono font-bold text-slate-400">
                    {formatUptime(stats?.uptime_seconds ?? 0)}
                  </span>
                </div>
                {isRunning && (
                  <div className="flex items-center gap-1.5 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    <span className="text-[9px] font-black text-emerald-400">LIVE</span>
                  </div>
                )}
              </div>
            </div>

            {/* Network Infrastructure Card */}
            <div className="flex flex-col gap-5 p-6 bg-white/[0.03] rounded-[28px] border border-white/[0.05] backdrop-blur-sm shadow-xl">
              <div className="flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/10 group-hover:bg-blue-500/20 transition-colors">
                    <Wifi className="w-4 h-4 text-blue-400" />
                  </div>
                  <span className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest">VPN Cycle</span>
                </div>
                <span className="text-lg font-black text-white">{stats?.vpn_rotations ?? 0}</span>
              </div>

              <div className="h-px bg-white/[0.03]" />

              <div className="flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/10 group-hover:bg-purple-500/20 transition-colors">
                    <Clock className="w-4 h-4 text-purple-400" />
                  </div>
                  <span className="text-[10px] text-slate-400 font-extrabold uppercase tracking-widest">Active Units</span>
                </div>
                <span className="text-lg font-black text-white">{status?.active_browsers ?? 0}</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
