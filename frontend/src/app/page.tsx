'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import {
  CheckCircle2, XCircle, AlertTriangle, Wifi, Clock, Zap, RefreshCw, Globe, Power,
  Search, Clipboard, Trash2, FileUp, ExternalLink, Loader2, X, HelpCircle, Layers, Settings2, Activity,
  Shield, ShieldAlert, Cpu, Network, Maximize2, Minimize2, Copy, Check
} from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import { LogViewer } from '@/components/LogViewer';
import { botApi, BotStatus, LogEntry } from '@/lib/api';

// --- Types & Config ---
type ResultStatus = 'success' | 'invalid' | 'banned' | 'error' | 'pending' | 'retrying' | 'security_block';

interface AccountResult {
  id: string;
  email: string;
  reddit_password: string | null;
  status: ResultStatus;
  username: string | null;
  karma: number | null;
  remark: string | null;
  profile_url: string | null;
  vpn_location: string | null;
  vpn_ip: string | null;
  created_at: string;
}

const STATUS_CONFIG: Record<ResultStatus, { label: string; icon: React.ElementType; color: string; bg: string }> = {
  success: { label: 'Valid', icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  invalid: { label: 'Invalid', icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-400/10' },
  banned: { label: 'Banned', icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-400/10' },
  error: { label: 'Error', icon: HelpCircle, color: 'text-slate-400', bg: 'bg-slate-400/10' },
  pending: { label: 'Pending', icon: Clock, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  retrying: { label: 'Retrying', icon: RefreshCw, color: 'text-amber-400', bg: 'bg-amber-400/10' },
  security_block: { label: 'Blocked', icon: ShieldAlert, color: 'text-rose-500', bg: 'bg-rose-500/10' },
};

// --- Helpers ---
function formatUptime(secs: number): string {
  if (!secs) return "00:00:00";
  const h = Math.floor(secs / 3600).toString().padStart(2, '0');
  const m = Math.floor((secs % 3600) / 60).toString().padStart(2, '0');
  const s = (secs % 60).toString().padStart(2, '0');
  return `${h}:${m}:${s}`;
}

function StatusBadge({ status }: { status: ResultStatus }) {
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;
  return (
    <div className={clsx("inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold tracking-wide", cfg.bg, cfg.color)}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </div>
  );
}

export default function DashboardPage() {
  // Bot Status & Logs
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [logsCopied, setLogsCopied] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Growth Controls
  const [batchLimit, setBatchLimit] = useState(100);
  const [parallelBrowsers, setParallelBrowsers] = useState(1);

  // Account State
  const [results, setResults] = useState<AccountResult[]>([]);
  const [filter, setFilter] = useState<ResultStatus | 'all'>('pending');
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingResults, setLoadingResults] = useState(true);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [pasting, setPasting] = useState(false);
  const [isLogsMaximized, setIsLogsMaximized] = useState(false);
  const [showStartModal, setShowStartModal] = useState(false);
  const [selectedStatuses, setSelectedStatuses] = useState<ResultStatus[]>(['pending', 'error']);

  // --- Handlers ---
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const [{ data: sData }, { data: rData }] = await Promise.all([
        botApi.status(),
        botApi.results()
      ]);
      setStatus(sData);
      setLogs(sData.recent_logs ?? []);
      setResults(Array.isArray(rData) ? rData : []);
      setBackendOnline(true);
      setLoadingResults(false);
    } catch {
      setBackendOnline(false);
    } finally {
      setRefreshing(false);
    }
  };

  const refreshOnlyStatus = useCallback(async () => {
    try {
      const { data } = await botApi.status();
      setStatus(data);

      // Smart Log Merge: Prevent vanishing by merging new logs with existing local state
      setLogs(prev => {
        const incoming = data.recent_logs ?? [];
        if (prev.length === 0) return incoming;

        // Find logs that aren't already in the list (using timestamp + message as key)
        const lastLocal = prev[prev.length - 1];
        const newOnes = incoming.filter(l =>
          !prev.some(p => p.timestamp === l.timestamp && p.message === l.message)
        );

        const combined = [...prev, ...newOnes].slice(-1000); // Keep local buffer of 1000
        return combined;
      });

      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  const refreshOnlyResults = useCallback(async () => {
    try {
      const { data } = await botApi.results();
      setResults(Array.isArray(data) ? data : []);
      setLoadingResults(false);
    } catch { }
  }, []);

  useEffect(() => {
    handleRefresh();
    // LIVE UPDATE: Faster polling for both status and results (2s)
    const sInterval = setInterval(refreshOnlyStatus, 2000);
    const rInterval = setInterval(refreshOnlyResults, 2000);
    return () => { clearInterval(sInterval); clearInterval(rInterval); };
  }, [refreshOnlyStatus, refreshOnlyResults]);

  const handleToggleBot = async () => {
    if (isRunning) {
      setRefreshing(true);
      try {
        await botApi.stop();
        setTimeout(handleRefresh, 1000);
      } catch (e) { console.error(e); }
      finally { setRefreshing(false); }
    } else {
      setShowStartModal(true);
    }
  };

  const confirmStartBot = async () => {
    setShowStartModal(false);
    setRefreshing(true);
    try {
      await botApi.start(undefined, parallelBrowsers, batchLimit, selectedStatuses);
      setTimeout(handleRefresh, 1000);
    } catch (e) {
      console.error(e);
      alert('❌ Failed to start bot: ' + (e as any).message);
    } finally {
      setRefreshing(false);
    }
  };

  const handlePasteSubmit = async () => {
    if (!pasteText.trim()) return;
    setPasting(true);
    try {
      const { data } = await botApi.pasteCredentials(pasteText);
      if (data.status === 'success') {
        setShowPasteModal(false);
        setPasteText('');
        handleRefresh();
      } else { alert('❌ ' + data.message); }
    } catch (err: any) { alert('❌ Failed: ' + (err.response?.data?.detail || err.message)); }
    finally { setPasting(false); }
  };

  const handleCopyLogs = useCallback(() => {
    if (logs.length === 0) return;
    const logText = logs.map(l => `[${l.timestamp}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(logText).then(() => {
      setLogsCopied(true);
      setTimeout(() => setLogsCopied(false), 2000);
    });
  }, [logs]);

  // --- Computed ---
  const isRunning = (status?.is_running ?? false) || (status?.is_starting ?? false);
  const isStarting = status?.is_starting ?? false;
  const dbStats = status?.stats?.db_stats;
  const total = dbStats?.total ?? 0;
  // Accounts are only 'finished' if they are NOT pending, NOT retrying, and NOT security_blocked
  const inProgress = (dbStats?.pending ?? 0) + (dbStats?.retrying ?? 0) + (dbStats?.security_block ?? 0);
  const finished = total - inProgress;
  const progressPercent = total > 0 ? Math.round((finished / total) * 100) : 0;
  const successRate = total > 0 && finished > 0
    ? Math.round(((dbStats?.success ?? 0) / finished) * 100)
    : 0;

  const filtered = useMemo(() => {
    return (filter === 'all' ? results : results.filter(r => r.status === filter))
      .filter(r =>
        r.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.username?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false)
      );
  }, [results, filter, searchQuery]);

  const counts = {
    all: results.length,
    success: results.filter(r => r.status === 'success').length,
    invalid: results.filter(r => r.status === 'invalid').length,
    banned: results.filter(r => r.status === 'banned').length,
    error: results.filter(r => r.status === 'error').length,
    pending: results.filter(r => r.status === 'pending').length,
  };

  return (
    <div className="min-h-screen bg-[#0d1424] text-slate-200 p-3 sm:p-4 lg:p-6 flex flex-col gap-3 sm:gap-4 overflow-x-hidden">

      {/* ── TOP HEADER CONTAINER ────────────────────────────────────────── */}
      <div className="max-w-full mx-auto w-full flex flex-col gap-3 sm:gap-4 overflow-hidden">

        {/* Connection & Telemetry Header */}
        <div className="bg-white/5 border border-white/10 rounded-lg overflow-hidden shadow-xl">
          <div className="flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-white/10">

            {/* Primary Status Section */}
            <div className="lg:w-2/5 p-3 sm:p-4 md:p-6 flex flex-col sm:flex-row items-center justify-between gap-4 md:gap-8 bg-gradient-to-br from-[#ff5a5f]/5 to-transparent">
              <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
                <div className="flex flex-col items-center gap-1 sm:gap-2">
                  <button
                    onClick={handleToggleBot}
                    disabled={refreshing}
                    className={clsx(
                      "w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16 rounded-full flex items-center justify-center transition-all shadow-lg active:scale-95 border-2",
                      isRunning
                        ? "bg-rose-500/20 border-rose-500/50 text-rose-400 shadow-rose-500/10 animate-pulse"
                        : "bg-emerald-500/20 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/30"
                    )}
                  >
                    <Power className="w-5 h-5 sm:w-6 sm:h-6 md:w-8 md:h-8" />
                  </button>
                  <span className={clsx("text-[8px] sm:text-[9px] font-black uppercase tracking-[0.2em]", isRunning ? "text-rose-400" : "text-emerald-400")}>
                    {isRunning ? "STOP" : "START"}
                  </span>
                </div>
                <div className="flex flex-col">
                  <span className={clsx("text-sm sm:text-base md:text-xl font-bold tracking-tight", isRunning ? "text-rose-400" : "text-slate-300")}>
                    {isRunning ? "Connected" : "Disconnected"}
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <div className={clsx("w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full", isRunning ? "bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.6)]" : "bg-emerald-400")} />
                    <span className="text-[9px] sm:text-[10px] text-white font-bold uppercase tracking-wide bg-white/10 px-1.5 sm:px-2 py-0.5 rounded whitespace-nowrap">
                      {status?.vpn_location || 'Connecting...'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Growth Controls Inline (Relocated for better mobile flow) */}
              <div className="flex items-center gap-3 bg-white/5 p-2 px-3 rounded-lg border border-white/5">
                <div className="flex flex-col">
                  <span className="text-[8px] text-slate-500 font-bold uppercase tracking-tighter">Batch</span>
                  <input
                    type="number"
                    value={batchLimit}
                    onChange={(e) => setBatchLimit(parseInt(e.target.value) || 1)}
                    className="w-12 bg-black/40 border-none px-1 text-xs font-bold text-center text-[#ff5a5f] outline-none"
                  />
                </div>
                <div className="w-px h-6 bg-white/10" />
                <div className="flex flex-col">
                  <span className="text-[8px] text-slate-500 font-bold uppercase tracking-tighter">Load</span>
                  <input
                    type="number"
                    value={parallelBrowsers}
                    onChange={(e) => setParallelBrowsers(parseInt(e.target.value) || 1)}
                    className="w-12 bg-black/40 border-none px-1 text-xs font-bold text-center text-[#ff5a5f] outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Telemetry Tiles Grid */}
            <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-white/10">

              {/* Uptime Tile (New Position) */}
              <div className="p-3 sm:p-4 flex flex-col justify-between hover:bg-white/2 transition-colors">
                <span className="text-[8px] sm:text-[9px] font-bold text-slate-500 uppercase tracking-widest">Uptime</span>
                <div className="flex items-end gap-1 sm:gap-2 mt-1">
                  <span className="text-lg sm:text-2xl font-mono font-bold text-white leading-none tracking-tight">{formatUptime(status?.stats?.uptime_seconds ?? 0)}</span>
                  <Clock className="w-3 h-3 sm:w-4 sm:h-4 text-amber-400 mb-0.5" />
                </div>
              </div>

              <div className="p-3 sm:p-4 flex flex-col justify-between hover:bg-white/2 transition-colors">
                <span className="text-[8px] sm:text-[9px] font-bold text-slate-500 uppercase tracking-widest">Active Units</span>
                <div className="flex items-end gap-1 sm:gap-2 mt-1">
                  <span className="text-lg sm:text-2xl font-bold text-white leading-none">{status?.active_browsers || 0}</span>
                  <Cpu className="w-3 h-3 sm:w-4 sm:h-4 text-blue-400 mb-0.5" />
                </div>
              </div>

              {/* Rotations Tile */}
              <div className="p-3 sm:p-4 flex flex-col justify-between hover:bg-white/2 transition-colors border-t border-white/10 sm:border-t-0 sm:border-l border-white/10 lg:border-l-0">
                <span className="text-[8px] sm:text-[9px] font-bold text-slate-500 uppercase tracking-widest">Network Cycles</span>
                <div className="flex items-end gap-1 sm:gap-2 mt-1">
                  <span className="text-lg sm:text-2xl font-bold text-white leading-none">{status?.stats?.vpn_rotations || 0}</span>
                  <RefreshCw className="w-3 h-3 sm:w-4 sm:h-4 text-emerald-400 mb-0.5" />
                </div>
              </div>

              {/* Success Rate Tile */}
              <div className="p-3 sm:p-4 flex flex-col justify-between hover:bg-white/2 transition-colors border-t border-white/10 sm:border-t-0">
                <div className="flex items-center justify-between">
                  <span className="text-[8px] sm:text-[9px] font-bold text-slate-500 uppercase tracking-widest">Success Rate</span>
                  <span className="text-[9px] sm:text-[10px] font-bold text-emerald-400">{successRate}%</span>
                </div>
                <div className="mt-1 sm:mt-2 h-1 bg-white/5 rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${successRate}%` }} className="h-full bg-emerald-500" />
                </div>
              </div>


            </div>
          </div>
        </div>

        {/* ── PROGRESS & ACTIONS ───────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-4">

          {/* Progress Panel */}
          <div className="lg:col-span-8 bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col justify-between gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-[#ff5a5f]">
                <Activity className="w-4 h-4" />
                <span className="text-[11px] font-bold tracking-widest">Progress</span>
              </div>
              <div className="flex items-center gap-2 sm:gap-4 text-[10px] font-bold">
                <span className="text-slate-500">{finished} / {total}</span>
                <span className="text-[#ff5a5f]">{progressPercent}%</span>
              </div>
            </div>
            <div className="h-2.5 bg-black/40 rounded-full overflow-hidden p-0.5 border border-white/5 shadow-inner">
              <motion.div initial={{ width: 0 }} animate={{ width: `${progressPercent}%` }} className="h-full bg-[#ff5a5f] rounded-full shadow-[0_0_12px_rgba(255,90,95,0.4)]" />
            </div>
          </div>

          {/* Quick Actions Panel */}
          <div className="lg:col-span-4 bg-white/5 border border-white/10 rounded-lg p-3">
            <div className="flex items-center gap-2 h-full min-h-[44px]">
              <button
                onClick={() => setShowPasteModal(true)}
                disabled={isRunning || pasting}
                className={clsx(
                  "flex-1 h-full group relative overflow-hidden rounded-md font-bold text-[11px] flex items-center justify-center gap-2 transition-all shadow-lg active:scale-[0.98] py-2",
                  (isRunning || pasting)
                    ? "bg-white/5 text-slate-500 border border-white/5 cursor-not-allowed"
                    : "bg-[#ff5a5f] hover:bg-[#ff5a5f]/90 text-white"
                )}
              >
                <Clipboard className="w-4 h-4" />
                {isRunning ? "Running..." : "Paste"}
              </button>
              <button
                onClick={() => document.getElementById('file-upload-main')?.click()}
                className="flex-1 h-full flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-white/5 border border-white/10 rounded-md hover:bg-white/10 text-xs font-bold text-slate-300 transition-all"
              >
                <FileUp className="w-4 h-4" />
                Upload
                <input type="file" id="file-upload-main" className="hidden" onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    try { await botApi.uploadCredentials(file); handleRefresh(); }
                    catch (err: any) { alert(err.message); }
                  }
                }} />
              </button>
            </div>
          </div>

        </div>

        {/* ── LOGS & ACTIVITY ──────────────────────────────────────────── */}
        <div className="bg-white/5 border border-white/10 rounded-lg overflow-hidden flex flex-col group/logs">
          <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Logs</span>
              {isRunning && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 rounded text-[9px] font-bold text-emerald-400 border border-emerald-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> Live
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* RESTORED: Copy logs button */}
              <button
                onClick={handleCopyLogs}
                className="p-1 px-2.5 hover:bg-white/5 rounded transition-all flex items-center gap-1.5 text-slate-500 hover:text-white border border-transparent hover:border-white/10 active:scale-95"
              >
                {logsCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span className={clsx("text-[10px] font-bold uppercase", logsCopied && "text-emerald-400")}>
                  {logsCopied ? "Copied" : "Copy"}
                </span>
              </button>
              <div className="w-px h-4 bg-white/10 mx-1" />
              <button onClick={handleRefresh} className="p-1 px-2 hover:bg-white/5 rounded transition-colors flex items-center gap-1.5 text-slate-500 hover:text-white">
                <RefreshCw className={clsx("w-3.5 h-3.5", refreshing && "animate-spin")} />
                <span className="text-[10px] font-bold uppercase tracking-tight">Refresh</span>
              </button>
              <button
                onClick={() => setIsLogsMaximized(true)}
                className="p-1.5 hover:bg-white/5 rounded text-slate-500 hover:text-white transition-colors"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          <div className="h-56 relative">
            <LogViewer logs={logs} className="h-full" />
          </div>
        </div>

        {/* ── INVENTORY TABLE ──────────────────────────────────────────── */}
        <section className="flex flex-col gap-4 mt-2">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              Account List <span className="text-xs font-normal text-slate-500 opacity-50">[{results.length} total]</span>
            </h2>
          </div>

          {/* Search and Filter Bar */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 px-1">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/5 overflow-x-auto scrollbar-hide h-10">
              {(['all', 'pending', 'success', 'invalid', 'banned', 'error'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={clsx(
                    "px-4 h-full rounded-md text-[10px] font-bold border transition-all capitalize whitespace-nowrap flex items-center justify-center gap-2",
                    filter === f
                      ? "bg-[#ff5a5f] border-[#ff5a5f] text-white shadow-lg shadow-[#ff5a5f]/20"
                      : "border-transparent text-slate-500 hover:text-slate-200"
                  )}
                >
                  {f} <span className="px-1.5 py-0.5 bg-black/30 rounded text-[9px] opacity-60 font-mono tracking-tighter">{counts[f]}</span>
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="relative flex-1 md:flex-none md:w-80 group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-[#ff5a5f] transition-colors" />
              <input
                type="text"
                placeholder="Search cluster data..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 bg-white/5 border border-white/5 rounded-lg text-xs text-slate-200 outline-none focus:border-[#ff5a5f]/50 h-10 transition-all placeholder:text-slate-600 focus:bg-white/[0.08]"
              />
            </div>
          </div>

          {/* Industrial Grid Style Table */}
          <div className="bg-white/5 border border-white/10 rounded-lg overflow-hidden shadow-2xl backdrop-blur-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-white/[0.03] border-b border-white/10">
                    <th className="px-4 py-3 text-left font-bold text-slate-500 tracking-wider text-[10px] w-[240px]">Identity (Checked)</th>
                    <th className="px-4 py-3 text-left font-bold text-slate-500 tracking-wider text-[10px] w-[150px]">Password</th>
                    <th className="px-4 py-3 text-left font-bold text-slate-500 tracking-wider text-[10px] w-[120px]">VPN Location</th>
                    <th className="px-4 py-3 text-left font-bold text-slate-500 tracking-wider text-[10px] w-[120px]">VPN IP</th>
                    <th className="px-4 py-3 text-center font-bold text-slate-500 tracking-wider text-[10px] w-[100px]">Verification</th>
                    <th className="px-4 py-3 text-center font-bold text-slate-500 tracking-wider text-[10px] w-[100px]">Status</th>
                    <th className="px-4 py-3 text-left font-bold text-slate-500 tracking-wider text-[10px]">Remark</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.05]">
                  {loadingResults ? (
                    <tr><td colSpan={7} className="py-20 text-center text-slate-600 font-bold tracking-widest animate-pulse">Synchronizing Cluster Data...</td></tr>
                  ) : filtered.length === 0 ? (
                    <tr><td colSpan={7} className="py-24 text-center">
                      <div className="flex flex-col items-center gap-3 opacity-20">
                        <Search className="w-12 h-12" />
                        <span className="font-bold tracking-widest text-xs italic">No data matched the current query</span>
                      </div>
                    </td></tr>
                  ) : (
                    filtered.map((res, idx) => (
                      <tr key={res.id} className={clsx("hover:bg-white/[0.04] transition-colors group", idx % 2 === 1 && "bg-white/[0.01]")}>
                        <td className="px-4 py-4 font-mono select-all font-extrabold whitespace-nowrap">
                          <div className="flex items-center gap-2 group/email">
                            <span className="text-emerald-400 truncate max-w-[210px] font-black drop-shadow-[0_0_8px_rgba(52,211,153,0.2)]">
                              {res.email}
                            </span>
                            <div className="flex items-center gap-1 opacity-0 group-hover/email:opacity-100 transition-opacity">
                              <button
                                onClick={() => handleCopy(res.email || '', `email-${res.id}`)}
                                className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-500 transition-colors"
                                title="Copy Email"
                              >
                                {copiedId === `email-${res.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              </button>
                              {res.profile_url && (
                                <a
                                  href={res.profile_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="p-1 rounded bg-white/5 hover:bg-white/10 text-[#ff5a5f] transition-colors"
                                  title="View Profile"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2 group/pass">
                            <code className="text-[11px] font-mono text-slate-200 bg-white/5 px-2 py-1 rounded truncate max-w-[120px] font-bold">
                              {res.reddit_password || '••••••••'}
                            </code>
                            {res.reddit_password && (
                              <button
                                onClick={() => handleCopy(res.reddit_password || '', `pass-${res.id}`)}
                                className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-500 transition-colors opacity-0 group-hover/pass:opacity-100"
                                title="Copy Password"
                              >
                                {copiedId === `pass-${res.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className="text-[11px] font-bold text-slate-300">
                            {res.vpn_location || '—'}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <code className="text-[10px] font-mono text-slate-400 bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
                            {res.vpn_ip || '—'}
                          </code>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <div className="flex flex-col items-center">
                            <span className="text-[11px] font-black text-rose-400 tabular-nums">
                              {res.karma?.toLocaleString() || '0'}
                            </span>
                            <span className="text-[8px] text-slate-600 font-bold tracking-tighter">Karma</span>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <StatusBadge status={res.status} />
                        </td>
                        <td className="px-4 py-4 max-w-sm">
                          <span className="text-slate-500 font-bold text-[11px] leading-relaxed line-clamp-2 italic">
                            {res.remark || '—'}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

      </div>

      {/* ── MODALS ─────────────────────────────────────────────────── */}

      {/* Maximized Logs Overlay */}
      <AnimatePresence>
        {isLogsMaximized && (
          <div className="fixed inset-0 z-[120] flex flex-col p-6 overflow-hidden">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsLogsMaximized(false)} className="absolute inset-0 bg-black/95 backdrop-blur-md" />
            <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="relative z-10 w-full max-w-6xl mx-auto flex-1 flex flex-col bg-[#0d1424] border border-white/10 rounded-xl shadow-4xl overflow-hidden mt-8">
              <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/[0.03]">
                <div className="flex items-center gap-4">
                  <span className="p-2 bg-[#ff5a5f]/10 rounded-lg"><Activity className="w-5 h-5 text-[#ff5a5f]" /></span>
                  <div className="flex flex-col">
                    <h2 className="text-lg font-bold text-white leading-tight underline decoration-[#ff5a5f]/30 underline-offset-4">Full Spectrum Activity Log</h2>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Protocol Version 4.2 // Master Cluster Stream</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleCopyLogs}
                    className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-xs font-bold text-slate-300 flex items-center gap-2 transition-all active:scale-95 border border-white/10"
                  >
                    {logsCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    {logsCopied ? "Protocol Copied" : "Copy All Logs"}
                  </button>
                  <button onClick={() => setIsLogsMaximized(false)} className="p-2 hover:bg-white/5 text-slate-500 hover:text-white rounded-lg transition-colors">
                    <Minimize2 className="w-6 h-6" />
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                {/* When maximized, we can use the main logs which are now merged up to 1000 locally */}
                <LogViewer logs={logs} className="h-full" />
              </div>
              <div className="p-4 bg-white/[0.02] border-t border-white/10 flex justify-between items-center text-[10px] text-slate-600 font-bold tracking-widest px-8">
                <span>Live Stream Active</span>
                <span>Buffer: {logs.length} entries</span>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Start Selection Modal */}
      <AnimatePresence>
        {showStartModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowStartModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.98, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.98, opacity: 0 }} className="bg-[#0d1424] w-full max-w-md rounded-xl p-6 border border-white/10 shadow-3xl relative z-10 flex flex-col gap-5">
              <div className="flex items-center justify-between border-b border-white/5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                    <Power className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div className="flex flex-col">
                    <h3 className="text-base font-bold text-white tracking-tight">Start Bot</h3>
                    <p className="text-[10px] text-slate-500 font-bold tracking-widest">Select accounts to process</p>
                  </div>
                </div>
                <button onClick={() => setShowStartModal(false)} className="p-1.5 hover:bg-white/5 text-slate-600 hover:text-white rounded-lg transition-colors"><X className="w-5 h-5" /></button>
              </div>

              <div className="grid grid-cols-1 gap-2 py-2">
                {(['pending', 'error', 'success', 'invalid', 'banned'] as ResultStatus[]).map(s => (
                  <button
                    key={s}
                    onClick={() => {
                      setSelectedStatuses(prev =>
                        prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
                      );
                    }}
                    className={clsx(
                      "flex items-center justify-between p-3 rounded-lg border transition-all text-xs font-bold tracking-wide group",
                      selectedStatuses.includes(s)
                        ? "bg-white/5 border-emerald-500/30 text-emerald-400 shadow-lg shadow-emerald-500/5"
                        : "bg-black/20 border-white/5 text-slate-500 hover:border-white/10 hover:text-slate-300"
                    )}
                  >
                    <div className="flex items-center gap-3 capitalize">
                      <div className={clsx("w-2 h-2 rounded-full", selectedStatuses.includes(s) ? "bg-emerald-400" : "bg-slate-700")} />
                      {s}
                    </div>
                    {selectedStatuses.includes(s) && <CheckCircle2 className="w-4 h-4" />}
                  </button>
                ))}
              </div>

              <div className="flex flex-col gap-3 pt-2">
                <button
                  onClick={confirmStartBot}
                  disabled={selectedStatuses.length === 0}
                  className="w-full py-3 bg-[#ff5a5f] text-white rounded-lg text-xs font-black tracking-[0.1em] hover:bg-[#ff5a5f]/90 shadow-xl shadow-[#ff5a5f]/20 disabled:opacity-30 flex items-center justify-center gap-2 transition-all active:scale-95"
                >
                  <Zap className="w-4 h-4" />
                  Start
                </button>
                <button onClick={() => setShowStartModal(false)} className="text-[10px] font-bold text-slate-600 tracking-widest hover:text-slate-400 transition-colors py-1">
                  Cancel
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Paste Modal */}
      <AnimatePresence>
        {showPasteModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowPasteModal(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.98, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.98, opacity: 0 }} className="bg-[#0d1424] w-full max-w-2xl rounded-xl p-8 border border-white/10 shadow-3xl relative z-10 flex flex-col gap-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-[#ff5a5f]/10 flex items-center justify-center border border-[#ff5a5f]/20">
                    <Clipboard className="w-6 h-6 text-[#ff5a5f]" />
                  </div>
                  <div className="flex flex-col">
                    <h3 className="text-xl font-bold text-white tracking-tight">Paste Accounts</h3>
                    <p className="text-xs text-slate-500 font-medium">Enter accounts in email:password format, one per line.</p>
                  </div>
                </div>
                <button onClick={() => setShowPasteModal(false)} className="p-2 hover:bg-white/5 text-slate-600 hover:text-white rounded-lg transition-colors"><X className="w-6 h-6" /></button>
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold tracking-widest px-1">
                  <span>Format: email:password</span>
                  <span className="text-[#ff5a5f]">Required Entry</span>
                </div>
                <textarea
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                  placeholder="user1@example.com:pass123\nuser2@example.com:pass456"
                  className="w-full h-80 bg-black/50 border border-white/10 rounded-xl p-6 font-mono text-xs text-slate-300 outline-none focus:border-[#ff5a5f]/50 resize-none shadow-inner leading-relaxed"
                />
              </div>

              <div className="flex justify-end gap-3 mt-2">
                <button onClick={() => setShowPasteModal(false)} className="px-6 py-2.5 text-xs font-bold text-slate-500 hover:text-slate-200 transition-all">Cancel</button>
                <button
                  onClick={handlePasteSubmit}
                  disabled={pasting || !pasteText.trim()}
                  className="px-8 py-2.5 bg-[#ff5a5f] text-white rounded-lg text-xs font-bold hover:bg-[#ff5a5f]/90 shadow-xl shadow-[#ff5a5f]/20 disabled:opacity-30 flex items-center gap-2 group transition-all active:scale-95"
                >
                  {pasting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4 group-hover:animate-pulse" />}
                  Save
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
