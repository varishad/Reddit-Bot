'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield,
    Users,
    Key,
    RefreshCw,
    Search,
    MoreVertical,
    CheckCircle2,
    XCircle,
    Clock,
    Lock,
    Edit2,
    Copy,
    UserPlus,
    X
} from 'lucide-react';
import { botApi } from '@/lib/api';

interface ManagedUser {
    id: string;
    username: string | null;
    license_key: string;
    is_active: boolean;
    role: string;
    plan_name: string;
    plan_start_date: string | null;
    plan_end_date: string | null;
    machine_id: string | null;
    last_login: string | null;
}

export default function AdminPage() {
    const [users, setUsers] = useState<ManagedUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [resetModal, setResetModal] = useState<{ open: boolean; license: string }>({ open: false, license: '' });
    const [newPassword, setNewPassword] = useState('');
    const [resetStatus, setResetStatus] = useState<{ msg: string; type: 'success' | 'error' | '' }>({ msg: '', type: '' });
    const [createModalOpen, setCreateModalOpen] = useState(false);
    const [newUserData, setNewUserData] = useState({
        username: '',
        license_key: '',
        password: '',
        role: 'User',
        plan_name: 'Monthly Normal',
        days: 30
    });
    const [createStatus, setCreateStatus] = useState<{ msg: string; type: 'success' | 'error' | '' }>({ msg: '', type: '' });

    const generateLicense = () => {
        const segments = Array.from({ length: 3 }, () =>
            Math.random().toString(36).substring(2, 6).toUpperCase()
        );
        setNewUserData({ ...newUserData, license_key: `REDDIT-${segments.join('-')}` });
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            const response = await botApi.getUsers();
            setUsers(response.data);
        } catch (err) {
            console.error('Failed to fetch users:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async () => {
        if (!newPassword) return;
        try {
            const response = await botApi.resetPassword(resetModal.license, newPassword);
            setResetStatus({ msg: response.data.message, type: 'success' });
            setTimeout(() => {
                setResetModal({ open: false, license: '' });
                setNewPassword('');
                setResetStatus({ msg: '', type: '' });
            }, 2000);
        } catch (err: any) {
            setResetStatus({ msg: err.response?.data?.detail || 'Reset failed', type: 'error' });
        }
    };

    const handleCreateUser = async () => {
        if (!newUserData.username || !newUserData.license_key || !newUserData.password) return;
        try {
            await botApi.createUser(newUserData);
            setCreateStatus({ msg: 'User created successfully!', type: 'success' });
            setTimeout(() => {
                setCreateModalOpen(false);
                setCreateStatus({ msg: '', type: '' });
                setNewUserData({
                    username: '',
                    license_key: '',
                    password: '',
                    role: 'User',
                    plan_name: 'Monthly Normal',
                    days: 30
                });
                fetchUsers();
            }, 1500);
        } catch (err: any) {
            setCreateStatus({ msg: err.response?.data?.detail || 'Creation failed', type: 'error' });
        }
    };

    const filteredUsers = users.filter(u =>
        u.license_key.toLowerCase().includes(search.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <div className="p-6 lg:p-10 space-y-8 pb-12">
            {/* Header & Subtitle */}
            <div>
                <div className="flex items-center gap-3 mb-2">
                    <Shield className="text-emerald-500" size={32} />
                    <h1 className="text-3xl font-bold text-white">Admin Control Center</h1>
                </div>
                <p className="text-gray-400 text-sm">Monitor system health, manage licenses, and reset device security.</p>
            </div>

            {/* Admin Info - Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl">
                    <div className="flex items-center gap-4">
                        <div className="p-3 rounded-2xl bg-indigo-500/10 border border-indigo-500/20">
                            <Users className="text-indigo-400" size={24} />
                        </div>
                        <div>
                            <div className="text-xs text-gray-500 uppercase tracking-widest font-bold">Total Licenses</div>
                            <div className="text-2xl font-bold text-white">{users.length}</div>
                        </div>
                    </div>
                </div>

                <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl">
                    <div className="flex items-center gap-4">
                        <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                            <CheckCircle2 className="text-emerald-400" size={24} />
                        </div>
                        <div>
                            <div className="text-xs text-gray-500 uppercase tracking-widest font-bold">Active Today</div>
                            <div className="text-2xl font-bold text-white">
                                {users.filter(u => u.is_active).length}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-6 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl">
                    <div className="flex items-center gap-4">
                        <div className="p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20">
                            <Clock className="text-rose-400" size={24} />
                        </div>
                        <div>
                            <div className="text-xs text-gray-500 uppercase tracking-widest font-bold">Expired / Inactive</div>
                            <div className="text-2xl font-bold text-white">
                                {users.filter(u => !u.is_active || (u.plan_end_date && new Date(u.plan_end_date) < new Date())).length}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="glass rounded-3xl overflow-hidden border border-white/10">
                {/* Toolbar */}
                <div className="p-6 border-b border-white/5 bg-white/[0.01] flex flex-col md:flex-row gap-4 items-center">
                    <div className="relative flex-1 w-full">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                        <input
                            type="text"
                            placeholder="Search by License Key..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-black/20 border border-white/10 rounded-2xl py-3 pl-12 pr-4 text-white placeholder:text-gray-600 focus:outline-none focus:border-emerald-500/40 focus:ring-1 focus:ring-emerald-500/40 transition-all"
                        />
                    </div>
                    <button
                        onClick={() => {
                            generateLicense();
                            setCreateModalOpen(true);
                        }}
                        className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-accent hover:bg-rose-600 text-white transition-all font-bold text-sm whitespace-nowrap shadow-lg shadow-accent/20"
                    >
                        <UserPlus size={16} />
                        Add New User
                    </button>
                    <button
                        onClick={fetchUsers}
                        className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-white/[0.05] border border-white/10 hover:bg-white/10 text-gray-300 transition-all font-medium text-sm whitespace-nowrap"
                    >
                        <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                        Refresh Data
                    </button>
                </div>

                {/* User Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="text-[10px] font-bold text-gray-500 uppercase tracking-widest bg-white/[0.02] border-b border-white/5">
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4">User</th>
                                <th className="px-6 py-4">License Key</th>
                                <th className="px-6 py-4">Plan Name</th>
                                <th className="px-6 py-4">Start Date</th>
                                <th className="px-6 py-4">Expiry Date</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.05]">
                            {filteredUsers.map((u) => (
                                <motion.tr
                                    key={u.id}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="hover:bg-white/[0.02] transition-colors group"
                                >
                                    <td className="px-6 py-4">
                                        {u.is_active ? (
                                            <div className="flex items-center gap-2 text-emerald-500 text-xs font-medium">
                                                <CheckCircle2 size={14} />
                                                Active
                                            </div>
                                        ) : (
                                            <div className="flex items-center gap-2 text-gray-500 text-xs font-medium">
                                                <XCircle size={14} />
                                                Inactive
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2 text-white text-sm font-semibold">
                                            {u.username || '—'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2 group/key">
                                            <span className="font-mono text-white text-sm tracking-tight">{u.license_key}</span>
                                            <button
                                                onClick={() => { navigator.clipboard.writeText(u.license_key); }}
                                                className="p-1.5 rounded-lg bg-white/5 hover:bg-emerald-500/20 text-gray-500 hover:text-emerald-500 transition-all opacity-0 group-hover/key:opacity-100"
                                                title="Copy License"
                                            >
                                                <Copy size={12} />
                                            </button>
                                        </div>
                                        <div className="text-[10px] text-gray-500 font-mono mt-1 opacity-50">
                                            {u.machine_id ? `HWID: ${u.machine_id.slice(-6)}` : 'No Hardware Lock'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="px-2 py-0.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-bold uppercase tracking-tight">
                                            {u.plan_name || 'Monthly Normal'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-xs text-gray-400 font-medium">
                                            {(u as any).plan_start_date ? new Date((u as any).plan_start_date).toLocaleDateString() : 'N/A'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2 text-xs font-semibold text-white">
                                            <Clock size={12} className="text-gray-500" />
                                            {u.plan_end_date ? new Date(u.plan_end_date).toLocaleDateString() : '—'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <button
                                                onClick={() => setResetModal({ open: true, license: u.license_key })}
                                                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500 hover:text-white transition-all text-[10px] font-bold border border-emerald-500/20"
                                            >
                                                <Key size={12} />
                                                RESET
                                            </button>
                                        </div>
                                    </td>
                                </motion.tr>
                            ))}
                            {filteredUsers.length === 0 && (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500 italic">No licenses found matching your search.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Password Reset Modal */}
            <AnimatePresence>
                {resetModal.open && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setResetModal({ open: false, license: '' })}
                            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            className="relative w-full max-w-md p-8 rounded-3xl bg-zinc-900 border border-white/10 shadow-2xl"
                        >
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-3 rounded-2xl bg-accent/10">
                                    <Lock className="text-accent" size={24} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-white">Reset Password</h3>
                                    <p className="text-gray-400 text-sm">For: {resetModal.license}</p>
                                </div>
                            </div>

                            <div className="space-y-4 mb-8">
                                <div>
                                    <label className="text-xs font-medium text-gray-500 uppercase tracking-widest block mb-1.5">New Secure Password</label>
                                    <input
                                        type="text"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="Enter temporary password..."
                                        className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 px-6 text-white focus:outline-none focus:border-accent"
                                    />
                                </div>
                                {resetStatus.msg && (
                                    <p className={clsx("text-sm text-center font-medium", resetStatus.type === 'success' ? 'text-emerald-500' : 'text-rose-500')}>
                                        {resetStatus.msg}
                                    </p>
                                )}
                            </div>

                            <div className="flex gap-4">
                                <button
                                    disabled={!newPassword || resetStatus.type === 'success'}
                                    onClick={handleResetPassword}
                                    className="flex-1 py-4 rounded-2xl bg-accent text-white font-bold hover:bg-accent-light transition-all disabled:opacity-50"
                                >
                                    Confirm Reset
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Create User Modal */}
            <AnimatePresence>
                {createModalOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setCreateModalOpen(false)}
                            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            className="relative w-full max-w-xl p-8 rounded-3xl bg-zinc-900 border border-white/10 shadow-2xl overflow-y-auto max-h-[90vh]"
                        >
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-3 rounded-2xl bg-accent/10">
                                        <UserPlus className="text-accent" size={24} />
                                    </div>
                                    <div>
                                        <h3 className="text-xl font-bold text-white">Add New User</h3>
                                        <p className="text-gray-400 text-sm">Create a new license and user profile</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setCreateModalOpen(false)}
                                    className="p-2 rounded-xl hover:bg-white/5 text-gray-500 transition-all"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                                <div className="space-y-4">
                                    <div>
                                        <label className="text-xs font-medium text-gray-500 uppercase tracking-widest block mb-1.5">Username</label>
                                        <input
                                            type="text"
                                            value={newUserData.username}
                                            onChange={(e) => setNewUserData({ ...newUserData, username: e.target.value })}
                                            placeholder="John Doe"
                                            className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-accent"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-xs font-medium text-gray-500 uppercase tracking-widest block mb-1.5">Default Password</label>
                                        <input
                                            type="text"
                                            value={newUserData.password}
                                            onChange={(e) => setNewUserData({ ...newUserData, password: e.target.value })}
                                            placeholder="Secure password..."
                                            className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-accent"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div>
                                        <div className="flex justify-between items-center mb-1.5">
                                            <label className="text-xs font-medium text-gray-500 uppercase tracking-widest">License Key</label>
                                            <button onClick={generateLicense} className="text-[10px] text-accent font-bold hover:underline">Regenerate</button>
                                        </div>
                                        <input
                                            type="text"
                                            value={newUserData.license_key}
                                            onChange={(e) => setNewUserData({ ...newUserData, license_key: e.target.value.toUpperCase() })}
                                            className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 px-4 text-white font-mono text-xs focus:outline-none focus:border-accent"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-medium text-gray-500 uppercase tracking-widest block mb-1.5">Role</label>
                                            <select
                                                value={newUserData.role}
                                                onChange={(e) => setNewUserData({ ...newUserData, role: e.target.value })}
                                                className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 px-3 text-white text-sm focus:outline-none focus:border-accent appearance-none cursor-pointer"
                                            >
                                                <option value="User">User</option>
                                                <option value="Admin">Admin</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-xs font-medium text-gray-500 uppercase tracking-widest block mb-1.5">Days</label>
                                            <input
                                                type="number"
                                                value={newUserData.days}
                                                onChange={(e) => setNewUserData({ ...newUserData, days: parseInt(e.target.value) })}
                                                className="w-full bg-black/40 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-accent"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {createStatus.msg && (
                                <p className={clsx("text-sm text-center font-medium mb-6", createStatus.type === 'success' ? 'text-emerald-500' : 'text-rose-500')}>
                                    {createStatus.msg}
                                </p>
                            )}

                            <button
                                disabled={!newUserData.username || !newUserData.license_key || !newUserData.password || createStatus.type === 'success'}
                                onClick={handleCreateUser}
                                className="w-full py-4 rounded-2xl bg-accent text-white font-bold hover:bg-rose-600 transition-all disabled:opacity-50 shadow-lg shadow-accent/20"
                            >
                                {createStatus.type === 'success' ? 'User Created!' : 'Create New User Account'}
                            </button>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}

function clsx(...classes: any[]) {
    return classes.filter(Boolean).join(' ');
}
