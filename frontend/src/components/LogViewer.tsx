'use client';

import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { Copy, Check } from 'lucide-react';
import type { LogEntry } from '@/lib/api';

interface LogViewerProps {
    logs: LogEntry[];
}

function getLogColor(type: LogEntry['type']) {
    switch (type) {
        case 'success': return 'text-emerald-400';
        case 'error': return 'text-rose-400';
        case 'warning': return 'text-amber-400';
        default: return 'text-slate-300';
    }
}

function classifyLog(message: string): LogEntry['type'] {
    const m = message.toLowerCase();
    if (m.includes('success') || m.includes('✅') || m.includes('completed')) return 'success';
    if (m.includes('error') || m.includes('❌') || m.includes('critical') || m.includes('failed')) return 'error';
    if (m.includes('warning') || m.includes('⚠️') || m.includes('warn')) return 'warning';
    return 'info';
}

export function LogViewer({ logs }: LogViewerProps) {
    const [copied, setCopied] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const handleCopy = () => {
        if (logs.length === 0) return;

        const logText = logs
            .map(log => `[${log.timestamp}] ${log.message}`)
            .join('\n');

        navigator.clipboard.writeText(logText).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="glass rounded-2xl overflow-hidden flex flex-col h-72">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs font-semibold text-slate-300 uppercase tracking-widest">
                        Live Activity
                    </span>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] text-slate-600 font-medium">{logs.length} entries</span>
                    <button
                        onClick={handleCopy}
                        disabled={logs.length === 0}
                        title="Copy logs"
                        className="p-1 px-2 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/10 transition-all text-slate-400 hover:text-slate-200 flex items-center gap-1.5 active:scale-95 disabled:opacity-30"
                    >
                        {copied ? (
                            <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-[10px] font-medium text-emerald-400">Copied</span>
                            </>
                        ) : (
                            <>
                                <Copy className="w-3 h-3" />
                                <span className="text-[10px] font-medium">Copy</span>
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Log entries */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs space-y-0.5 scrollbar-thin scrollbar-thumb-white/10 select-text cursor-text"
            >
                {logs.length === 0 ? (
                    <p className="text-slate-600 italic py-4 text-center">Waiting for bot activity...</p>
                ) : (
                    logs.map((log, i) => {
                        const type = log.type || classifyLog(log.message);
                        return (
                            <div key={i} className="flex gap-3 leading-relaxed">
                                <span className="text-slate-600 flex-shrink-0">{log.timestamp}</span>
                                <span className={clsx('break-all', getLogColor(type))}>{log.message}</span>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
