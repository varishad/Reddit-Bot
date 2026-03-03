'use client';

import { useState, useEffect, useCallback } from 'react';
import { Download, Trash2 } from 'lucide-react';
import { LogViewer } from '@/components/LogViewer';
import { botApi, LogEntry } from '@/lib/api';

export default function LogsPage() {
    const [logs, setLogs] = useState<LogEntry[]>([]);

    const fetchLogs = useCallback(async () => {
        try {
            const { data } = await botApi.logs();
            setLogs(data);
        } catch { }
    }, []);

    useEffect(() => {
        fetchLogs();
        const id = setInterval(fetchLogs, 2000);
        return () => clearInterval(id);
    }, [fetchLogs]);

    const downloadLogs = () => {
        const text = logs.map(l => `[${l.timestamp}] ${l.message}`).join('\n');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bot-logs-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="flex flex-col gap-6 p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Activity Logs</h1>
                    <p className="text-slate-500 text-sm mt-0.5">Real-time bot event stream</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setLogs([])}
                        className="p-2.5 rounded-xl glass hover:border-white/20 transition-all duration-200 text-slate-400 hover:text-rose-400"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                    <button
                        onClick={downloadLogs}
                        className="p-2.5 rounded-xl glass hover:border-white/20 transition-all duration-200 text-slate-400 hover:text-slate-200"
                    >
                        <Download className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Full-height expanded log viewer */}
            <div className="glass rounded-2xl overflow-hidden flex flex-col" style={{ height: 'calc(100vh - 160px)' }}>
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-xs font-semibold text-slate-300 uppercase tracking-widest">Live Feed</span>
                    </div>
                    <span className="text-xs text-slate-600">{logs.length} entries</span>
                </div>
                <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs space-y-0.5">
                    {logs.length === 0 ? (
                        <p className="text-slate-600 italic py-8 text-center">No activity yet — start the bot to see logs here.</p>
                    ) : (
                        logs.map((log, i) => (
                            <div key={i} className="flex gap-3 leading-relaxed">
                                <span className="text-slate-600 flex-shrink-0">{log.timestamp}</span>
                                <span className={
                                    log.type === 'success' ? 'text-emerald-400' :
                                        log.type === 'error' ? 'text-rose-400' :
                                            log.type === 'warning' ? 'text-amber-400' :
                                                'text-slate-300'
                                }>{log.message}</span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
