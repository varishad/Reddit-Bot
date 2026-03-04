'use client';

import { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import type { LogEntry } from '@/lib/api';

interface LogViewerProps {
    logs: LogEntry[];
    className?: string;
}

function getLogColor(type: LogEntry['type']) {
    switch (type) {
        case 'success': return 'text-emerald-400';
        case 'error': return 'text-rose-400';
        case 'warning': return 'text-amber-400';
        default: return 'text-slate-400';
    }
}

function classifyLog(message: string): LogEntry['type'] {
    const m = message.toLowerCase();
    if (m.includes('success') || m.includes('✅') || m.includes('completed')) return 'success';
    if (m.includes('error') || m.includes('❌') || m.includes('critical') || m.includes('failed')) return 'error';
    if (m.includes('warning') || m.includes('⚠️') || m.includes('warn')) return 'warning';
    return 'info';
}

export function LogViewer({ logs, className }: LogViewerProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div
            ref={scrollRef}
            className={clsx(
                "overflow-y-auto font-mono text-[11px] space-y-1 scrollbar-thin scrollbar-thumb-white/10 select-text cursor-text p-4",
                className
            )}
        >
            {logs.length === 0 ? (
                <div className="flex items-center justify-center h-full opacity-20 italic text-[10px] uppercase tracking-widest">
                    Awaiting System Signal...
                </div>
            ) : (
                logs.map((log, i) => {
                    const type = log.type || classifyLog(log.message);
                    return (
                        <div key={i} className="flex gap-3 leading-relaxed border-l border-white/5 pl-3 hover:bg-white/[0.02] transition-colors">
                            <span className="text-slate-600 flex-shrink-0 tabular-nums">[{log.timestamp}]</span>
                            <span className={clsx('break-all', getLogColor(type))}>{log.message}</span>
                        </div>
                    );
                })
            )}
        </div>
    );
}
