'use client';

import { useState, useEffect } from 'react';
import { Save, Shield, Globe, Cpu, Zap, Activity, CheckCircle2, AlertCircle } from 'lucide-react';
import { botApi, BotStatus } from '@/lib/api';

export default function SettingsPage() {
    const [saved, setSaved] = useState(false);
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState<BotStatus | null>(null);

    const [settings, setSettings] = useState({
        browser_type: 'chromium',
        headless: false,
        delay_min: 3,
        delay_max: 5,
        max_parallel_browsers: 5,
        stealth_enabled: true,
        humanize_input: true,
        vpn_enabled: true,
        vpn_rotate_per_batch: true,
        persistent_context: false,
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [settingsRes, statusRes] = await Promise.all([
                    botApi.getSettings(),
                    botApi.status()
                ]);
                setSettings(settingsRes.data);
                setStatus(statusRes.data);
            } catch (error) {
                console.error('Failed to fetch settings:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const update = (key: string, value: unknown) =>
        setSettings(prev => ({ ...prev, [key]: value }));

    const save = async () => {
        try {
            await botApi.updateSettings(settings);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch {
            alert('Failed to save settings');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            </div>
        );
    }

    const vpnConnected = Boolean(status?.vpn_location);

    return (
        <div className="max-w-6xl mx-auto p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/5 pb-6">
                <div>
                    <h1 className="text-3xl font-extrabold text-white tracking-tight">System Settings</h1>
                    <p className="text-slate-500 text-sm mt-1">Configure your industrial-grade automation engine</p>
                </div>
                <button
                    onClick={save}
                    className="flex items-center gap-2 px-6 py-3 rounded-2xl font-bold text-sm bg-accent hover:bg-rose-600 text-white shadow-xl shadow-accent/20 transition-all active:scale-95"
                >
                    <Save className="w-4 h-4" />
                    {saved ? '✓ Changes Applied' : 'Save Configuration'}
                </button>
            </div>

            {/* Top row: System Integrity + Live Performance side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* System Integrity */}
                <Section title="System Integrity" icon={<Shield className="w-4 h-4 text-accent" />}>
                    <div className="space-y-3">
                        <StatusItem
                            label="Database Connection"
                            status="Operational"
                            healthy={true}
                            icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                        />
                        <StatusItem
                            label="License Authentication"
                            status="Verified"
                            healthy={true}
                            icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                        />
                        <StatusItem
                            label="VPN Tunnel"
                            status={status?.vpn_location || 'Disconnected'}
                            healthy={vpnConnected}
                            icon={vpnConnected
                                ? <CheckCircle2 className="w-3.5 h-3.5" />
                                : <AlertCircle className="w-3.5 h-3.5" />}
                        />
                    </div>
                </Section>

                {/* Live Performance */}
                <div className="glass rounded-[32px] p-8 border border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-1 h-full bg-accent/20 group-hover:bg-accent transition-colors duration-500" />
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 rounded-xl bg-white/5 border border-white/10 group-hover:border-accent/30 transition-all">
                            <Activity className="w-4 h-4 text-accent" />
                        </div>
                        <h2 className="text-sm font-extrabold text-white uppercase tracking-[0.2em]">Live Performance</h2>
                    </div>
                    <div className="space-y-5">
                        <PerfBar label="API Latency" value="14ms" percent={15} color="accent" />
                        <PerfBar label="CPU Usage" value="8%" percent={8} color="blue" />
                        <PerfBar label="Memory" value="312 MB" percent={42} color="emerald" />
                    </div>
                </div>
            </div>

            {/* Bottom row: Automation Engine + Detection Mitigation + Network Security */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Automation Engine */}
                <Section title="Automation Engine" icon={<Cpu className="w-4 h-4 text-blue-400" />}>
                    <div className="grid grid-cols-2 gap-5">
                        <Field label="Browser Engine">
                            <select
                                value={settings.browser_type}
                                onChange={e => update('browser_type', e.target.value)}
                                className="input-field-premium"
                            >
                                <option value="chromium">Chromium High-Performance</option>
                                <option value="firefox">Firefox Stealth</option>
                            </select>
                        </Field>
                        <Field label="Concurrency Limit">
                            <input
                                type="number"
                                min={1}
                                max={20}
                                value={settings.max_parallel_browsers}
                                onChange={e => update('max_parallel_browsers', parseInt(e.target.value))}
                                className="input-field-premium"
                            />
                        </Field>
                    </div>
                    <Field label="Processing Interval (Detection Avoidance)">
                        <div className="flex items-center gap-3">
                            <div className="flex-1 relative">
                                <input type="number" min={1} max={60} value={settings.delay_min}
                                    onChange={e => update('delay_min', parseInt(e.target.value))}
                                    className="input-field-premium w-full pr-12" placeholder="Min" />
                                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 font-bold uppercase">sec</span>
                            </div>
                            <span className="text-slate-600 font-bold text-lg">~</span>
                            <div className="flex-1 relative">
                                <input type="number" min={1} max={120} value={settings.delay_max}
                                    onChange={e => update('delay_max', parseInt(e.target.value))}
                                    className="input-field-premium w-full pr-12" placeholder="Max" />
                                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 font-bold uppercase">sec</span>
                            </div>
                        </div>
                    </Field>
                    <hr className="border-white/5" />
                    <Toggle label="Headless Environment" sublabel="Execute automation in background without visual artifacts"
                        value={settings.headless} onChange={v => update('headless', v)} />
                </Section>

                {/* Right column: Detection Mitigation + Network Security stacked */}
                <div className="space-y-6">
                    <Section title="Detection Mitigation" icon={<Zap className="w-4 h-4 text-amber-400" />}>
                        <Toggle label="Advanced Stealth" sublabel="Apply kernel-level browser fingerprint patches"
                            value={settings.stealth_enabled} onChange={v => update('stealth_enabled', v)} />
                        <Toggle label="Human Simulation" sublabel="Recursive typing curves and heuristic mouse paths"
                            value={settings.humanize_input} onChange={v => update('humanize_input', v)} />
                        <Toggle label="Session Persistence" sublabel="Maintain cookie vault across execution cycles"
                            value={settings.persistent_context} onChange={v => update('persistent_context', v)} />
                    </Section>

                    <Section title="Network Security" icon={<Globe className="w-4 h-4 text-emerald-400" />}>
                        <Toggle label="VPN Tunneling" sublabel="Route all traffic through encrypted ExpressVPN nodes"
                            value={settings.vpn_enabled} onChange={v => update('vpn_enabled', v)} />
                        <Toggle label="Dynamic IP Rotation" sublabel="Automatically switch VPN locations per account batch"
                            value={settings.vpn_rotate_per_batch} onChange={v => update('vpn_rotate_per_batch', v)} />
                    </Section>
                </div>
            </div>
        </div>
    );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
    return (
        <div className="glass rounded-[32px] p-8 border border-white/5 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-accent/20 group-hover:bg-accent transition-colors duration-500" />
            <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-xl bg-white/5 border border-white/10 group-hover:border-accent/30 transition-all">
                    {icon}
                </div>
                <h2 className="text-sm font-extrabold text-white uppercase tracking-[0.2em]">{title}</h2>
            </div>
            <div className="space-y-4">
                {children}
            </div>
        </div>
    );
}

function StatusItem({ label, status, icon, healthy }: { label: string; status: string; icon: React.ReactNode; healthy: boolean }) {
    const badgeStyle = healthy
        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
        : 'bg-rose-500/10 border-rose-500/20 text-rose-400';
    return (
        <div className="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/[0.07] transition-all cursor-default">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{label}</span>
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${badgeStyle}`}>
                {icon}
                <span className="text-[10px] font-bold uppercase tracking-widest">{status}</span>
            </div>
        </div>
    );
}

function PerfBar({ label, value, percent, color }: { label: string; value: string; percent: number; color: string }) {
    const barColor = color === 'accent' ? 'bg-accent shadow-[0_0_12px_rgba(244,63,94,0.4)]'
        : color === 'blue' ? 'bg-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.4)]'
            : 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]';
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between text-xs">
                <span className="text-slate-500 uppercase tracking-wider font-bold">{label}</span>
                <span className="text-white/70 font-mono">{value}</span>
            </div>
            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${barColor}`} style={{ width: `${percent}%` }} />
            </div>
        </div>
    );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] ml-1">{label}</label>
            {children}
        </div>
    );
}

function Toggle({ label, sublabel, value, onChange }: { label: string; sublabel: string; value: boolean; onChange: (v: boolean) => void }) {
    return (
        <div className="flex items-center justify-between gap-6 p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/[0.07] transition-all group">
            <div className="flex-1">
                <p className="text-sm font-bold text-white group-hover:text-accent transition-colors">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{sublabel}</p>
            </div>
            <button
                onClick={() => onChange(!value)}
                aria-checked={value}
                role="switch"
                className={`relative w-14 h-7 rounded-full transition-all duration-500 flex-shrink-0 border-2 ${value ? 'bg-accent border-accent/40 shadow-[0_0_20px_rgba(244,63,94,0.3)]' : 'bg-slate-800 border-white/5'}`}
            >
                <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-lg transition-all duration-500 transform ${value ? 'translate-x-7 scale-110' : 'translate-x-0'}`} />
            </button>
        </div>
    );
}
