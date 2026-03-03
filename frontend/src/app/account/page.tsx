'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    User,
    Calendar,
    ShieldCheck,
    Key,
    Monitor,
    Clock,
    ChevronRight,
    AlertCircle
} from 'lucide-react';
import { botApi } from '@/lib/api';

interface UserInfo {
    license_key: string;
    is_active: boolean;
    plan_start_date: string | null;
    plan_end_date: string | null;
    plan_name: string;
    machine_id: string | null;
}

export default function AccountPage() {
    const [user, setUser] = useState<UserInfo | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const response = await botApi.userInfo();
                setUser(response.data);
            } catch (err) {
                console.error('Failed to fetch user info:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchUser();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
            </div>
        );
    }

    const daysLeft = user?.plan_end_date
        ? Math.max(0, Math.ceil((new Date(user.plan_end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)))
        : 0;

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'N/A';
        return new Date(dateStr).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    };

    return (
        <div className="p-6 lg:p-10 space-y-8 pb-12">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Account & Subscription</h1>
                <p className="text-gray-400">Manage your license and view device security details.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Subscription Status Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="lg:col-span-2 p-8 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl relative overflow-hidden group"
                >
                    <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
                        <ShieldCheck size={120} className="text-emerald-500" />
                    </div>

                    <div className="relative z-10">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                                <ShieldCheck className="text-emerald-500" size={24} />
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold text-white">Subscription Status</h2>
                                <span className="text-sm text-emerald-500 font-medium">Verified Account</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                            <div className="space-y-6">
                                <div>
                                    <label className="text-xs font-medium text-gray-500 uppercase tracking-widest mb-2 block">Current Plan</label>
                                    <div className="text-2xl font-bold text-white flex items-center gap-2">
                                        {user?.plan_name || 'Monthly Normal'}
                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">ACTIVE</span>
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex justify-between items-end">
                                        <label className="text-xs font-medium text-gray-500 uppercase tracking-widest">Time Remaining</label>
                                        <span className="text-emerald-500 font-medium">{daysLeft} Days</span>
                                    </div>
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${Math.min(100, (daysLeft / 30) * 100)}%` }}
                                            className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-6">
                                <div className="flex items-start gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
                                    <Calendar className="text-gray-500 mt-1" size={18} />
                                    <div>
                                        <div className="text-xs text-gray-500 mb-1 uppercase tracking-tighter">Start Date</div>
                                        <div className="text-white font-medium">{formatDate(user?.plan_start_date || null)}</div>
                                    </div>
                                </div>

                                <div className="flex items-start gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
                                    <Clock className="text-gray-500 mt-1" size={18} />
                                    <div>
                                        <div className="text-xs text-gray-500 mb-1 uppercase tracking-tighter">Expiry Date</div>
                                        <div className="text-white font-medium">{formatDate(user?.plan_end_date || null)}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* Support Card */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-8 rounded-3xl bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-white/[0.08] backdrop-blur-xl"
                >
                    <div className="h-full flex flex-col">
                        <h3 className="text-lg font-semibold text-white mb-4">Extend Access</h3>
                        <p className="text-gray-400 text-sm mb-8 leading-relaxed">
                            To renew or upgrade your monthly plan, please contact our support team. Your limits will be updated immediately.
                        </p>
                        <div className="mt-auto space-y-3">
                            <button className="w-full py-4 rounded-2xl bg-white text-black font-bold hover:bg-gray-200 transition-colors flex items-center justify-center gap-2">
                                Renewal Options
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Security Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="p-8 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl"
                >
                    <div className="flex items-center gap-3 mb-6">
                        <Key className="text-gray-400" size={20} />
                        <h3 className="text-lg font-semibold text-white">License Key</h3>
                    </div>
                    <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.05] font-mono text-emerald-400 select-all tracking-wider">
                        {user?.license_key}
                    </div>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="p-8 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl"
                >
                    <div className="flex items-center gap-3 mb-6">
                        <Monitor className="text-gray-400" size={20} />
                        <h3 className="text-lg font-semibold text-white">Device Security (HWID)</h3>
                    </div>
                    <div className="flex items-center justify-between p-4 rounded-2xl bg-black/40 border border-white/[0.05]">
                        <div className="font-mono text-gray-400 text-sm">
                            Fingerprint: <span className="text-white">...{user?.machine_id?.slice(-8)}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-medium text-emerald-500">
                            <ShieldCheck size={14} />
                            LOCKED
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Alert */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="flex items-center gap-3 p-4 rounded-2xl bg-amber-500/5 border border-amber-500/10 text-amber-500/80 text-sm"
            >
                <AlertCircle size={18} />
                Account access is strictly restricted to the primary hardware signature above.
            </motion.div>
        </div>
    );
}
