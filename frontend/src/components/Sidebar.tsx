'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
    LayoutDashboard, Users, Globe, ScrollText,
    Settings, Shield, HelpCircle, User, LogOut, Bot
} from 'lucide-react';
import { clsx } from 'clsx';
import { useState, useEffect } from 'react';
import { botApi } from '@/lib/api';

const primaryNav = [
    { label: 'Dashboard', href: '/', icon: LayoutDashboard },
    { label: 'Accounts', href: '/accounts', icon: Users },
    { label: 'VPN / Proxy', href: '/vpn', icon: Globe },
    { label: 'Logs', href: '/logs', icon: ScrollText },
];

const secondaryNav = [
    { label: 'How it works', href: '/how-it-works', icon: HelpCircle },
    { label: 'Settings', href: '/settings', icon: Settings },
    { label: 'Profile', href: '/account', icon: User },
];

const adminNav = [
    { label: 'Admin', href: '/admin', icon: Shield },
];

export function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [user, setUser] = useState<{
        license_key: string;
        username?: string;
        is_active: boolean;
        role?: string;
    } | null>(null);

    useEffect(() => {
        botApi.userInfo()
            .then(r => setUser(r.data))
            .catch(() => { });
    }, []);

    const displayName = user?.username && user.username !== 'Unknown'
        ? user.username
        : (user?.license_key?.slice(0, 10) ?? 'Loading...');
    const initials = displayName.slice(0, 2).toUpperCase();
    const isAdmin = user?.role === 'Admin';

    const handleLogout = async () => {
        try { await botApi.logout(); } catch { /* ignore */ }
        localStorage.removeItem('reddit_bot_auth_token');
        router.push('/login');
    };

    return (
        /*
         * Floating Sidebar — detached from the edges like ExpressVPN.
         */
        <aside
            className="fixed left-4 top-4 bottom-4 w-[230px] flex flex-col z-20 select-none rounded-[28px] shadow-[0_8px_32px_rgba(0,0,0,0.5)] border border-white/[0.04] overflow-hidden backdrop-blur-xl"
            style={{ background: '#0d1424' }}
        >
            {/* Subtle top glow — gives premium depth like ExpressVPN */}
            <div
                className="absolute top-0 left-0 right-0 h-48 pointer-events-none"
                style={{
                    background: 'radial-gradient(ellipse at 50% 0%, rgba(255,90,95,0.08) 0%, transparent 70%)',
                }}
            />

            {/* Logo */}
            <div className="flex items-center gap-2.5 px-5 h-[60px] flex-shrink-0 relative">
                <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center flex-shrink-0 shadow-lg shadow-accent/20">
                    <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <span className="font-bold text-white text-[13px] tracking-wide">Reddit Bot</span>
            </div>

            {/* Nav groups */}
            <div className="flex-1 flex flex-col gap-5 px-3 pt-2 overflow-y-auto">
                <NavGroup items={primaryNav} pathname={pathname} />
                <NavGroup label="More" items={secondaryNav} pathname={pathname} />
                {isAdmin && <NavGroup label="Admin" items={adminNav} pathname={pathname} />}
            </div>

            {/* User row — slim, subtle */}
            <div className="px-3 pb-4 pt-2">
                <div className="h-px bg-white/[0.05] mx-1 mb-3" />
                <div className="flex items-center gap-2 px-2 py-2 rounded-xl group cursor-default">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent to-rose-400 flex-shrink-0 flex items-center justify-center text-[9px] font-bold text-white">
                        {initials}
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                        <span className="text-[11px] font-semibold text-slate-300 truncate leading-tight">{displayName}</span>
                        <span className={clsx('text-[9px] font-medium leading-tight', user?.is_active ? 'text-emerald-400' : 'text-slate-600')}>
                            {user?.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <button
                        onClick={handleLogout}
                        title="Sign out"
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                    >
                        <LogOut className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        </aside>
    );
}

function NavGroup({
    label,
    items,
    pathname,
}: {
    label?: string;
    items: { label: string; href: string; icon: React.ElementType }[];
    pathname: string;
}) {
    return (
        <div>
            {label && (
                <p className="text-[9px] font-extrabold text-slate-700 uppercase tracking-[0.18em] px-2 pb-1.5">
                    {label}
                </p>
            )}
            <div className="space-y-0.5">
                {items.map(({ label, href, icon: Icon }) => {
                    const active = pathname === href;
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={clsx(
                                'flex items-center gap-2.5 px-2 py-[7px] rounded-xl transition-all duration-150 group',
                                active
                                    ? 'bg-white/[0.08] text-white'
                                    : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.04]'
                            )}
                        >
                            <Icon
                                className={clsx(
                                    'w-[15px] h-[15px] flex-shrink-0 transition-colors',
                                    active ? 'text-accent' : 'text-slate-600 group-hover:text-slate-300'
                                )}
                            />
                            <span className="text-[12.5px] font-medium flex-1">{label}</span>
                            {active && (
                                <span className="w-[5px] h-[5px] rounded-full bg-accent flex-shrink-0" />
                            )}
                        </Link>
                    );
                })}
            </div>
        </div>
    );
}
