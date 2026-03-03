'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import {
  CheckCircle2, XCircle, AlertTriangle, Wifi, Clock, Zap, RefreshCw, Globe
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
    <div className="min-h-screen">
      {/* Backend offline banner */}
      <AnimatePresence>
        {backendOnline === false && (
          <motion.div
            initial={{ y: -40 }}
            animate={{ y: 0 }}
            exit={{ y: -40 }}
            className="fixed top-0 left-0 right-0 z-50 bg-rose-600/90 text-white text-xs text-center py-2 font-semibold backdrop-blur"
          >
            ⚠️ Backend Offline — Run <code className="mx-1 bg-white/20 px-1 rounded">python3 server.py</code> to connect
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-8 p-6">
        {/* Minimal status row — no page title, just floating status like ExpressVPN */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Session indicator */}
            <span className="text-[11px] text-slate-600 font-medium">
              {status?.session_id ? `Session · ${status.session_id.slice(0, 8)}` : 'No active session'}
            </span>
            {/* VPN chip */}
            <div className={clsx(
              'flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border',
              status?.vpn_location
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-white/5 border-white/5 text-slate-600'
            )}>
              <Globe className="w-2.5 h-2.5" />
              {status?.vpn_location || 'Disconnected'}
            </div>
          </div>
          <button
            onClick={refresh}
            className="p-1.5 rounded-xl hover:bg-white/5 transition-all text-slate-600 hover:text-slate-300"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Power Button */}
        <div className="flex flex-col items-center py-6">
          <PowerButton
            isRunning={isRunning}
            onClick={handleToggle}
            disabled={actionLoading}
          />
          {isRunning && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-slate-500 mt-3"
            >
              Uptime: {formatUptime(stats?.uptime_seconds ?? 0)}
            </motion.p>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Checked"
            value={stats?.total ?? 0}
            icon={<Zap className="w-4 h-4" />}
            color="blue"
            subtitle="total accounts"
          />
          <StatCard
            label="Success"
            value={stats?.success ?? 0}
            icon={<CheckCircle2 className="w-4 h-4" />}
            color="green"
            subtitle={`${successRate}% rate`}
          />
          <StatCard
            label="Invalid"
            value={stats?.invalid ?? 0}
            icon={<XCircle className="w-4 h-4" />}
            color="red"
          />
          <StatCard
            label="Banned"
            value={stats?.banned ?? 0}
            icon={<AlertTriangle className="w-4 h-4" />}
            color="yellow"
          />
        </div>

        {/* Secondary stats row */}
        <div className="grid grid-cols-1 gap-4 text-center">
          <StatCard
            label="VPN Rotations"
            value={stats?.vpn_rotations ?? 0}
            icon={<Wifi className="w-4 h-4" />}
            color="blue"
          />
        </div>

        {/* Live Logs */}
        <LogViewer logs={logs} />
      </div>
    </div>
  );
}
