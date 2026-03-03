'use client';

import { useState } from 'react';
import { Save, Eye, EyeOff } from 'lucide-react';

export default function SettingsPage() {
    const [saved, setSaved] = useState(false);
    const [showKey, setShowKey] = useState(false);

    // These mirror config.py. In a real implementation you'd fetch/POST these via API.
    const [settings, setSettings] = useState({
        supabase_url: '',
        supabase_key: '',
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

    const update = (key: string, value: unknown) =>
        setSettings(prev => ({ ...prev, [key]: value }));

    const save = () => {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
        // TODO: POST to /settings endpoint when implemented
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Settings</h1>
                    <p className="text-slate-500 text-sm mt-0.5">Bot configuration</p>
                </div>
                <button
                    onClick={save}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-all"
                >
                    <Save className="w-4 h-4" />
                    {saved ? 'Saved!' : 'Save'}
                </button>
            </div>

            {/* Supabase */}
            <Section title="Supabase">
                <Field label="Project URL">
                    <input
                        type="text"
                        value={settings.supabase_url}
                        onChange={e => update('supabase_url', e.target.value)}
                        placeholder="https://xxxx.supabase.co"
                        className="input-field"
                    />
                </Field>
                <Field label="Service Role Key">
                    <div className="relative">
                        <input
                            type={showKey ? 'text' : 'password'}
                            value={settings.supabase_key}
                            onChange={e => update('supabase_key', e.target.value)}
                            placeholder="eyJhbGci..."
                            className="input-field pr-10"
                        />
                        <button
                            onClick={() => setShowKey(v => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                        >
                            {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                    </div>
                </Field>
            </Section>

            {/* Browser */}
            <Section title="Browser">
                <Field label="Browser Engine">
                    <select
                        value={settings.browser_type}
                        onChange={e => update('browser_type', e.target.value)}
                        className="input-field"
                    >
                        <option value="chromium">Chromium</option>
                        <option value="firefox">Firefox</option>
                    </select>
                </Field>
                <Field label="Max Parallel Browsers">
                    <input
                        type="number"
                        min={1}
                        max={20}
                        value={settings.max_parallel_browsers}
                        onChange={e => update('max_parallel_browsers', parseInt(e.target.value))}
                        className="input-field"
                    />
                </Field>
                <Field label="Delay Between Accounts (seconds)">
                    <div className="flex items-center gap-3">
                        <input type="number" min={1} max={60} value={settings.delay_min}
                            onChange={e => update('delay_min', parseInt(e.target.value))}
                            className="input-field w-24" placeholder="Min" />
                        <span className="text-slate-500 text-sm">to</span>
                        <input type="number" min={1} max={120} value={settings.delay_max}
                            onChange={e => update('delay_max', parseInt(e.target.value))}
                            className="input-field w-24" placeholder="Max" />
                    </div>
                </Field>
                <Toggle label="Headless Mode" sublabel="Run browsers invisibly in background"
                    value={settings.headless} onChange={v => update('headless', v)} />
            </Section>

            {/* Stealth */}
            <Section title="Stealth & Humanization">
                <Toggle label="Stealth Mode" sublabel="Apply anti-detection patches"
                    value={settings.stealth_enabled} onChange={v => update('stealth_enabled', v)} />
                <Toggle label="Humanize Input" sublabel="Simulate human typing and mouse movements"
                    value={settings.humanize_input} onChange={v => update('humanize_input', v)} />
                <Toggle label="Persistent Browser Profiles" sublabel="Reuse browser cookies across sessions"
                    value={settings.persistent_context} onChange={v => update('persistent_context', v)} />
            </Section>

            {/* VPN */}
            <Section title="VPN">
                <Toggle label="Enable VPN" sublabel="Use ExpressVPN for bot sessions"
                    value={settings.vpn_enabled} onChange={v => update('vpn_enabled', v)} />
                <Toggle label="Rotate VPN Per Batch" sublabel="Change VPN location between account batches"
                    value={settings.vpn_rotate_per_batch} onChange={v => update('vpn_rotate_per_batch', v)} />
            </Section>
        </div>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="glass rounded-2xl p-5 flex flex-col gap-4">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest border-b border-white/5 pb-3">{title}</h2>
            {children}
        </div>
    );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">{label}</label>
            {children}
        </div>
    );
}

function Toggle({ label, sublabel, value, onChange }: { label: string; sublabel: string; value: boolean; onChange: (v: boolean) => void }) {
    return (
        <label className="flex items-center justify-between gap-4 cursor-pointer group">
            <div>
                <p className="text-sm font-medium text-slate-200">{label}</p>
                <p className="text-xs text-slate-500">{sublabel}</p>
            </div>
            <button
                onClick={() => onChange(!value)}
                className={`relative w-11 h-6 rounded-full transition-all duration-300 flex-shrink-0 ${value ? 'bg-accent' : 'bg-slate-700'}`}
            >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-300 ${value ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
        </label>
    );
}
