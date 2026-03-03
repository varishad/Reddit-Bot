'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    CheckCircle2, XCircle, AlertTriangle, HelpCircle, RefreshCw,
    Search, Loader2, Clipboard, X, Clock
} from 'lucide-react';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

import { botApi } from '@/lib/api';
import { Skeleton, TableRowSkeleton } from '@/components/Skeleton';

type ResultStatus = 'success' | 'invalid' | 'banned' | 'error' | 'pending';

interface AccountResult {
    id: string;
    email: string;
    reddit_password: string | null;
    status: ResultStatus;
    username: string | null;
    karma: number | null;
    error_message: string | null;
    created_at: string;
}

const STATUS_CONFIG: Record<ResultStatus, { label: string; icon: React.ElementType; color: string; bg: string }> = {
    success: { label: 'Valid', icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
    invalid: { label: 'Invalid', icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-400/10' },
    banned: { label: 'Banned', icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-400/10' },
    error: { label: 'Error', icon: HelpCircle, color: 'text-slate-400', bg: 'bg-slate-400/10' },
    pending: { label: 'Ready', icon: Clock, color: 'text-blue-400', bg: 'bg-blue-400/10' },
};

function StatusBadge({ status }: { status: ResultStatus }) {
    const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.error;
    const Icon = cfg.icon;
    return (
        <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold', cfg.color, cfg.bg)}>
            <Icon className="w-3 h-3" />
            {cfg.label}
        </span>
    );
}

export default function AccountsPage() {
    const [results, setResults] = useState<AccountResult[]>([]);
    const [filter, setFilter] = useState<ResultStatus | 'all'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [showPasteModal, setShowPasteModal] = useState(false);
    const [pasteText, setPasteText] = useState('');
    const [pasting, setPasting] = useState(false);

    const fetchResults = useCallback(async () => {
        try {
            const { data } = await botApi.results();
            setResults(Array.isArray(data) ? data : []);
        } catch { }
        setLoading(false);
    }, []);

    const handlePasteSubmit = async () => {
        if (!pasteText.trim()) return;
        setPasting(true);
        try {
            const { data } = await botApi.pasteCredentials(pasteText);
            if (data.status === 'success') {
                alert('✅ ' + data.message);
                setShowPasteModal(false);
                setPasteText('');
            } else {
                alert('❌ ' + data.message);
            }
        } catch (err: any) {
            alert('❌ Failed to save: ' + (err.response?.data?.message || err.message));
        } finally {
            setPasting(false);
        }
    };

    useEffect(() => {
        fetchResults();
        const id = setInterval(fetchResults, 5000);
        return () => clearInterval(id);
    }, [fetchResults]);

    const filtered = (filter === 'all' ? results : results.filter(r => r.status === filter))
        .filter(r =>
            r.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (r.username?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false)
        );

    const counts = {
        all: results.length,
        success: results.filter(r => r.status === 'success').length,
        invalid: results.filter(r => r.status === 'invalid').length,
        banned: results.filter(r => r.status === 'banned').length,
        error: results.filter(r => r.status === 'error').length,
        pending: results.filter(r => r.status === 'pending').length,
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Accounts</h1>
                    <p className="text-slate-500 text-sm mt-0.5">Results from the current bot session</p>
                </div>
                <div className="flex gap-3">
                    <input
                        type="file"
                        id="import-accounts"
                        className="hidden"
                        accept=".txt,.csv"
                        onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                                setLoading(true);
                                try {
                                    const { data } = await botApi.uploadCredentials(file);
                                    if (data.status === 'success') {
                                        alert('✅ ' + data.message);
                                    } else {
                                        alert('❌ ' + data.message);
                                    }
                                } catch (err: any) {
                                    alert('❌ Failed to upload: ' + (err.response?.data?.message || err.message));
                                } finally {
                                    setLoading(false);
                                }
                            }
                        }}
                    />
                    <button
                        onClick={() => setShowPasteModal(true)}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass text-slate-300 font-semibold text-sm hover:text-white hover:border-white/20 transition-all"
                    >
                        <Clipboard className="w-4 h-4" />
                        Paste List
                    </button>
                    <button
                        onClick={() => document.getElementById('import-accounts')?.click()}
                        className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-accent text-white font-semibold text-sm hover:bg-accent/90 transition-all shadow-lg shadow-accent/20"
                    >
                        <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
                        Import Accounts
                    </button>
                    <button onClick={() => { setLoading(true); fetchResults(); }} className="p-2.5 rounded-xl glass hover:border-white/20 transition-all duration-200 text-slate-400 hover:text-slate-200">
                        <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
                    </button>
                </div>
            </div>

            {/* Controls Bar */}
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                {/* Filter Tabs */}
                <div className="flex gap-2 flex-wrap">
                    {(['all', 'pending', 'success', 'invalid', 'banned', 'error'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={clsx(
                                'px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 border',
                                filter === f
                                    ? 'bg-accent/20 text-accent border-accent/40'
                                    : 'glass text-slate-400 border-white/10 hover:text-slate-200'
                            )}
                        >
                            {f === 'all' ? 'All' : STATUS_CONFIG[f].label}
                            <span className="ml-1.5 text-slate-600 font-mono tracking-tight">{counts[f]}</span>
                        </button>
                    ))}
                </div>

                {/* Search */}
                <div className="relative w-full md:w-64 group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-accent transition-colors" />
                    <input
                        type="text"
                        placeholder="Search email or user..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-slate-200 outline-none focus:border-accent/40 focus:bg-accent/5 transition-all"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="glass rounded-2xl overflow-hidden min-h-[400px]">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-white/10 text-xs text-slate-500 uppercase tracking-wider">
                            <th className="text-left px-4 py-4 font-semibold">Email</th>
                            <th className="text-left px-4 py-4 font-semibold">Password</th>
                            <th className="text-left px-4 py-4 font-semibold">Username</th>
                            <th className="text-right px-4 py-4 font-semibold">Karma</th>
                            <th className="text-left px-4 py-4 font-semibold">Status</th>
                            <th className="text-left px-4 py-4 hidden md:table-cell font-semibold">Note</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {loading ? (
                            Array(8).fill(0).map((_, i) => <TableRowSkeleton key={i} />)
                        ) : filtered.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="py-24 text-center">
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
                                            <Search className="w-6 h-6 text-slate-600" />
                                        </div>
                                        <div>
                                            <p className="text-slate-400 font-medium">No accounts found</p>
                                            <p className="text-slate-600 text-xs mt-1">
                                                {searchQuery ? 'Try matching a different term' : 'Results will appear once the bot starts'}
                                            </p>
                                        </div>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            filtered.map(r => (
                                <tr key={r.id} className="hover:bg-accent/5 transition-colors group">
                                    <td className="px-4 py-3.5 text-slate-300 font-mono text-xs group-hover:text-slate-100 transition-colors">{r.email}</td>
                                    <td className="px-4 py-3.5 text-slate-400 font-mono text-xs group-hover:text-slate-200 transition-colors">
                                        {r.reddit_password ? (
                                            <span className="bg-white/5 px-1.5 py-0.5 rounded blur-[3px] hover:blur-none transition-all cursor-help" title="Hover to reveal">
                                                {r.reddit_password}
                                            </span>
                                        ) : '—'}
                                    </td>
                                    <td className="px-4 py-3.5 text-slate-400 group-hover:text-slate-200 transition-colors">{r.username ?? '—'}</td>
                                    <td className="px-4 py-3.5 text-right text-slate-400 group-hover:text-slate-200 transition-colors">{r.karma ?? '—'}</td>
                                    <td className="px-4 py-3.5">
                                        <StatusBadge status={r.status} />
                                    </td>
                                    <td className="px-4 py-3.5 text-slate-600 text-xs hidden md:table-cell max-w-xs truncate group-hover:text-slate-500 transition-colors">
                                        {r.error_message ?? '—'}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Paste Modal */}
            <AnimatePresence>
                {showPasteModal && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowPasteModal(false)}
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        >
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                exit={{ scale: 0.9, opacity: 0 }}
                                onClick={(e) => e.stopPropagation()}
                                className="glass w-full max-w-2xl rounded-2xl p-6 border border-white/10 shadow-2xl"
                            >
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                        <Clipboard className="w-5 h-5 text-accent" />
                                        Paste Account List
                                    </h3>
                                    <button onClick={() => setShowPasteModal(false)} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                                <p className="text-sm text-slate-500 mb-4">
                                    Paste your accounts in <code className="bg-white/5 px-1.5 py-0.5 rounded text-slate-300">email:password</code> format, one per line.
                                </p>
                                <textarea
                                    value={pasteText}
                                    onChange={(e) => setPasteText(e.target.value)}
                                    placeholder="user1@example.com:password123&#10;user2@example.com:password456"
                                    className="w-full h-80 bg-black/40 border border-white/10 rounded-xl p-4 text-slate-200 font-mono text-sm outline-none focus:border-accent/40 transition-all"
                                />
                                <div className="flex justify-end gap-3 mt-6">
                                    <button
                                        onClick={() => setShowPasteModal(false)}
                                        className="px-5 py-2.5 rounded-xl glass text-slate-400 font-semibold text-sm hover:text-white transition-all"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handlePasteSubmit}
                                        disabled={pasting || !pasteText.trim()}
                                        className="px-6 py-2.5 rounded-xl bg-accent text-white font-bold text-sm hover:opacity-90 transition-all disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {pasting && <Loader2 className="w-4 h-4 animate-spin" />}
                                        Save All
                                    </button>
                                </div>
                            </motion.div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
