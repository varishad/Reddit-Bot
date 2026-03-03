'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Users, Globe, ScrollText, Settings, Shield, HelpCircle, LogOut, User } from 'lucide-react';
import { clsx } from 'clsx';
import { useState, useEffect } from 'react';

import { botApi } from '@/lib/api';

const navItems = [
    { label: 'Dashboard', href: '/', icon: LayoutDashboard },
    { label: 'Accounts', href: '/accounts', icon: Users },
    { label: 'VPN / Proxy', href: '/vpn', icon: Globe },
    { label: 'Logs', href: '/logs', icon: ScrollText },
    { label: 'How it works', href: '/how-it-works', icon: HelpCircle },
    { label: 'Settings', href: '/settings', icon: Settings },
    { label: 'Profile', href: '/account', icon: User },
    { label: 'Admin', href: '/admin', icon: Shield },
];

export function Sidebar() {
    const pathname = usePathname();
    const [user, setUser] = useState<{ license_key: string; username?: string; is_active: boolean; role?: string } | null>(null);

    useEffect(() => {
        botApi.userInfo()
            .then(r => setUser(r.data))
            .catch(() => { });
    }, []);

    const displayName = user?.username && user.username !== 'Unknown' ? user.username : (user?.license_key ?? 'Loading...');
    const status = user?.is_active ? 'Active' : 'Inactive';

    const filteredNavItems = navItems.filter(item => {
        if (item.label === 'Admin' && user?.role !== 'Admin') return false;
        return true;
    });

    return (
        <aside className="glass fixed left-0 top-0 h-full w-16 md:w-56 flex flex-col py-6 px-2 md:px-4 z-20 border-r border-white/10">
            {/* Logo */}
            <div className="flex items-center gap-3 px-2 mb-10 select-none">
                <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-white" />
                </div>
                <span className="hidden md:block font-bold tracking-wide text-white text-sm">Reddit Bot</span>
            </div>

            {/* Nav */}
            <nav className="flex flex-col gap-1 flex-1">
                {filteredNavItems.map(({ label, href, icon: Icon }) => {
                    const active = pathname === href;
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={clsx(
                                'flex items-center gap-3 px-2 md:px-3 py-2.5 rounded-xl transition-all duration-200 group',
                                active
                                    ? 'bg-accent/20 text-accent'
                                    : 'text-slate-400 hover:text-slate-100 hover:bg-white/5'
                            )}
                        >
                            <Icon className={clsx('w-5 h-5 flex-shrink-0', active ? 'text-accent' : 'group-hover:text-slate-100')} />
                            <span className="hidden md:block text-sm font-medium">{label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom user pill */}
            <div className="hidden md:flex flex-col gap-2">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 group relative">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-accent to-rose-400 flex-shrink-0 flex items-center justify-center text-[10px] font-bold text-white">
                        {displayName.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                        <span className="text-xs font-semibold text-slate-200 truncate">{displayName}</span>
                        <span className={clsx('text-[10px] truncate', user?.is_active ? 'text-emerald-400' : 'text-slate-500')}>
                            {status}
                        </span>
                    </div>
                    <button
                        onClick={() => botApi.logout()}
                        className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-all opacity-0 group-hover:opacity-100"
                        title="Logout"
                    >
                        <LogOut className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </aside>
    );
}
