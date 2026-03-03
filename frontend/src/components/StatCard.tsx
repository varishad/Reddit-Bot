'use client';

import { clsx } from 'clsx';

interface StatCardProps {
    label: string;
    value: string | number;
    icon: React.ReactNode;
    color?: 'green' | 'red' | 'yellow' | 'blue' | 'default';
    subtitle?: string;
}

const colorMap = {
    green: 'text-emerald-400 bg-emerald-400/10',
    red: 'text-rose-400 bg-rose-400/10',
    yellow: 'text-amber-400 bg-amber-400/10',
    blue: 'text-sky-400 bg-sky-400/10',
    default: 'text-slate-400 bg-slate-400/10',
};

export function StatCard({ label, value, icon, color = 'default', subtitle }: StatCardProps) {
    const colorClass = colorMap[color];

    return (
        <div className="glass rounded-2xl p-5 flex flex-col gap-3 hover:border-white/20 hover:scale-[1.02] hover:shadow-2xl hover:shadow-black/20 transition-all-premium group cursor-default">
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-widest group-hover:text-slate-400 transition-colors">{label}</span>
                <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-500 group-hover:scale-110', colorClass)}>
                    {icon}
                </div>
            </div>
            <div>
                <span className="text-3xl font-bold text-slate-100 tracking-tight group-hover:text-white transition-colors">{value}</span>
                {subtitle && <p className="text-xs text-slate-500 mt-1.5 font-medium group-hover:text-slate-400 transition-colors">{subtitle}</p>}
            </div>
        </div>
    );
}
