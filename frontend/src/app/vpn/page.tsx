'use client';

import { useState, useEffect, useCallback } from 'react';
import { Wifi, WifiOff, Shuffle, PlugZap, MapPin, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { botApi, VPNDiagnostic } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface VPNStatus {
    connected: boolean;
    location: string | null;
}

export default function VPNPage() {
    const [vpn, setVpn] = useState<VPNStatus>({ connected: false, location: null });
    const [locations, setLocations] = useState<string[]>([]);
    const [selected, setSelected] = useState('');
    const [loading, setLoading] = useState(false);
    const [msg, setMsg] = useState('');

    // Diagnostics state
    const [showDiag, setShowDiag] = useState(false);
    const [diag, setDiag] = useState<VPNDiagnostic | null>(null);
    const [diagLoading, setDiagLoading] = useState(false);

    const runDiag = useCallback(async () => {
        setDiagLoading(true);
        try {
            const r = await botApi.vpnDiag();
            setDiag(r.data);
        } catch {
            setDiag(null);
        }
        setDiagLoading(false);
    }, []);

    useEffect(() => {
        if (showDiag) runDiag();
    }, [showDiag, runDiag]);

    const fetchStatus = useCallback(async () => {
        try {
            const r = await fetch(`${API_BASE}/vpn/status`);
            setVpn(await r.json());
        } catch { }
    }, []);

    const fetchLocations = useCallback(async () => {
        try {
            const r = await fetch(`${API_BASE}/vpn/locations`);
            const data = await r.json();
            const locs: string[] = Array.isArray(data) ? data : [];
            setLocations(locs);
            if (!selected && locs.length) setSelected(locs[0]);
        } catch { }
    }, [selected]);

    useEffect(() => {
        fetchStatus();
        fetchLocations();
        const id = setInterval(fetchStatus, 5000);
        return () => clearInterval(id);
    }, [fetchStatus, fetchLocations]);

    const post = async (url: string, params?: Record<string, string>) => {
        setLoading(true);
        setMsg('');
        try {
            const q = params ? '?' + new URLSearchParams(params).toString() : '';
            const r = await fetch(`${API_BASE}${url}${q}`, { method: 'POST' });
            const data = await r.json();
            setMsg(data.message ?? (data.success ? 'Done!' : 'Failed'));
            await fetchStatus();
        } catch (e) {
            setMsg('Network error');
        }
        setLoading(false);
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">VPN / Proxy</h1>
                    <p className="text-slate-500 text-sm mt-0.5">Network security and location management</p>
                </div>
                <button
                    onClick={() => setShowDiag(!showDiag)}
                    className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-accent transition-colors"
                >
                    {showDiag ? '[ Hide Diagnostics ]' : '[ Run Diagnostics ]'}
                </button>
            </div>

            {/* Diagnostics Panel */}
            {showDiag && (
                <div className="glass rounded-2xl p-5 border-amber-500/20 bg-amber-500/5 animate-in slide-in-from-top-2 duration-300">
                    <div className="flex items-center gap-2 mb-3 text-amber-400">
                        <AlertCircle className="w-4 h-4" />
                        <h3 className="text-xs font-bold uppercase tracking-widest">System Connection Diagnostics</h3>
                    </div>
                    {diagLoading ? (
                        <div className="py-4 flex justify-center"><div className="animate-spin h-4 w-4 border-b-2 border-amber-500 rounded-full" /></div>
                    ) : diag ? (
                        <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-4">
                                <DiagItem label="OS" value={diag.os === 'nt' ? 'Windows' : 'macOS/Linux'} />
                                <DiagItem label="App Installed" value={diag.is_mac ? 'Yes (ExpressVPN.app)' : 'Check manually'} />
                                <DiagItem label="CLI Found" value={diag.exe_found ? 'Yes' : 'No'} healthy={diag.exe_found} />
                                <DiagItem label="CLI Access" value={diag.cli_accessible ? 'Ready' : 'Blocker'} healthy={diag.cli_accessible} />
                            </div>
                            {diag.error_hint && (
                                <div className="mt-3 p-3 rounded-xl bg-black/20 border border-white/5">
                                    <p className="text-[10px] font-bold text-amber-500/80 uppercase mb-1">Recommended Action:</p>
                                    <p className="text-xs text-slate-300 leading-relaxed">{diag.error_hint}</p>
                                </div>
                            )}
                        </div>
                    ) : <p className="text-xs text-slate-500">Failed to load diagnostics</p>}
                </div>
            )}

            {/* Status card */}
            <div className={clsx(
                'glass rounded-2xl p-6 flex items-center justify-between transition-all duration-500',
                vpn.connected ? 'border-emerald-500/30' : 'border-white/10'
            )}>
                <div className="flex items-center gap-4">
                    <div className={clsx(
                        'w-14 h-14 rounded-2xl flex items-center justify-center',
                        vpn.connected ? 'bg-emerald-500/20' : 'bg-slate-700/50'
                    )}>
                        {vpn.connected
                            ? <Wifi className="w-7 h-7 text-emerald-400" />
                            : <WifiOff className="w-7 h-7 text-slate-500" />
                        }
                    </div>
                    <div>
                        <p className="font-bold text-white text-lg">
                            {vpn.connected ? 'Connected' : 'Disconnected'}
                        </p>
                        {vpn.connected && vpn.location && (
                            <p className="text-sm text-slate-400 flex items-center gap-1 mt-0.5">
                                <MapPin className="w-3 h-3" />{vpn.location}
                            </p>
                        )}
                    </div>
                </div>
                <div className={clsx(
                    'w-3 h-3 rounded-full',
                    vpn.connected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                )} />
            </div>

            {/* Controls */}
            <div className="glass rounded-2xl p-5 flex flex-col gap-4">
                <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Quick Controls</h2>
                <div className="grid grid-cols-2 gap-3">
                    <button
                        onClick={() => post('/vpn/connect', selected ? { location: selected } : undefined)}
                        disabled={loading || vpn.connected}
                        className="flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        <PlugZap className="w-4 h-4" />Connect
                    </button>
                    <button
                        onClick={() => post('/vpn/disconnect')}
                        disabled={loading || !vpn.connected}
                        className="flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        <WifiOff className="w-4 h-4" />Disconnect
                    </button>
                    <button
                        onClick={() => post('/vpn/connect')}
                        disabled={loading}
                        className="col-span-2 flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm glass border-white/10 text-slate-300 hover:text-white hover:bg-white/5 transition-all disabled:opacity-40"
                    >
                        <Shuffle className="w-4 h-4" />Random Location
                    </button>
                </div>
                {msg && <p className="text-xs text-slate-400 text-center">{msg}</p>}
            </div>

            {/* Location selector */}
            {locations.length > 0 && (
                <div className="glass rounded-2xl p-5 flex flex-col gap-3">
                    <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Available Locations</h2>
                    <div className="grid grid-cols-1 gap-1 max-h-64 overflow-y-auto pr-1">
                        {locations.map(loc => (
                            <button
                                key={loc}
                                onClick={() => setSelected(loc)}
                                className={clsx(
                                    'text-left px-3 py-2 rounded-xl text-sm transition-all duration-150',
                                    selected === loc
                                        ? 'bg-accent/20 text-accent border border-accent/30'
                                        : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                                )}
                            >
                                {loc}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function DiagItem({ label, value, healthy = true }: { label: string, value: string, healthy?: boolean }) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">{label}</span>
            <div className="flex items-center gap-1.5">
                <span className={clsx("text-xs font-bold", healthy ? "text-slate-200" : "text-amber-500")}>
                    {value}
                </span>
                {healthy ? (
                    <CheckCircle2 className="w-3 h-3 text-emerald-500/70" />
                ) : (
                    <XCircle className="w-3 h-3 text-amber-500/70" />
                )}
            </div>
        </div>
    );
}
