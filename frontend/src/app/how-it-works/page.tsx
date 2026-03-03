'use client';

import { motion } from 'framer-motion';
import {
    Shield,
    Zap,
    Globe,
    Lock,
    Cpu,
    Database,
    Search,
    CheckCircle2,
    ArrowRight
} from 'lucide-react';

const steps = [
    {
        title: 'Authentication & Session Initialization',
        description: 'The bot starts by validating your license key and setting up a secure session. It initializes the browser engine based on your settings (Chromium/Firefox).',
        icon: Lock,
        color: 'text-blue-400',
        bg: 'bg-blue-400/10'
    },
    {
        title: 'Stealth Browser Automation',
        description: 'Using advanced anti-detection patches (Stealth Mode), the bot simulates human-like movements, typing speeds, and mouse behaviors to bypass sophisticated bot detection.',
        icon: Cpu,
        color: 'text-purple-400',
        bg: 'bg-purple-400/10'
    },
    {
        title: 'Dynamic VPN & Proxy Rotation',
        description: 'To protect your accounts, the bot automatically rotates ExpressVPN locations and uses high-quality proxies, ensuring each account appears to originate from a unique, legitimate IP.',
        icon: Globe,
        color: 'text-emerald-400',
        bg: 'bg-emerald-400/10'
    },
    {
        title: 'Account Verification & Data Extraction',
        description: 'The bot logs into Reddit accounts, checks their status (Valid/Banned/Invalid), and extracts valuable data like Karma and account age in real-time.',
        icon: Search,
        color: 'text-amber-400',
        bg: 'bg-amber-400/10'
    },
    {
        title: 'Secure Data Synchronization',
        description: 'All results are instantly synced to your Supabase database and reflected in the dashboard, providing you with a live overview of your bot operations.',
        icon: Database,
        color: 'text-rose-400',
        bg: 'bg-rose-400/10'
    }
];

export default function HowItWorksPage() {
    return (
        <div className="flex flex-col gap-12 p-6">
            {/* Hero Section */}
            <header className="text-center space-y-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 text-accent text-xs font-bold uppercase tracking-wider mb-2">
                        <Shield className="w-3.5 h-3.5" />
                        Platform Guide
                    </span>
                    <h1 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight">
                        How it works
                    </h1>
                    <p className="text-slate-400 text-lg max-w-2xl mx-auto mt-4 leading-relaxed">
                        Reddit Bot uses industry-leading automation and stealth technology to manage your accounts with maximum efficiency and security.
                    </p>
                </motion.div>
            </header>

            {/* Steps Grid */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {steps.map((step, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: index * 0.1 }}
                        className="glass rounded-3xl p-6 flex flex-col gap-4 border border-white/5 hover:border-accent/30 transition-all-premium group"
                    >
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${step.bg} ${step.color} group-hover:scale-110 transition-transform duration-500`}>
                            <step.icon className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-white font-bold text-lg mb-2 flex items-center gap-2">
                                <span className="text-accent/40 text-sm font-mono">{index + 1}.</span>
                                {step.title}
                            </h3>
                            <p className="text-slate-500 text-sm leading-relaxed group-hover:text-slate-400 transition-colors">
                                {step.description}
                            </p>
                        </div>
                    </motion.div>
                ))}

                {/* Final Call to Action Card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: steps.length * 0.1 }}
                    className="bg-accent/10 border border-accent/20 rounded-3xl p-6 flex flex-col justify-between group hover:bg-accent/20 transition-all-premium"
                >
                    <div>
                        <Zap className="w-8 h-8 text-accent mb-4 group-hover:animate-pulse" />
                        <h3 className="text-white font-bold text-lg mb-2">Ready to Start?</h3>
                        <p className="text-accent/60 text-sm leading-relaxed">
                            Navigate to the Dashboard to initiate your first automated session.
                        </p>
                    </div>
                    <a
                        href="/"
                        className="mt-6 inline-flex items-center justify-center gap-2 bg-accent text-white py-3 rounded-2xl font-bold text-sm hover:scale-105 active:scale-95 transition-all"
                    >
                        Go to Dashboard
                        <ArrowRight className="w-4 h-4" />
                    </a>
                </motion.div>
            </section>

            {/* Advanced Features Section */}
            <section className="glass rounded-3xl p-8 mt-4 border border-white/5">
                <div className="flex flex-col md:flex-row gap-8 items-center">
                    <div className="flex-1 space-y-4">
                        <h2 className="text-2xl font-bold text-white">Elite Automation Core</h2>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Our core engine is built on modern browser automation frameworks enhanced with custom patches. Whether you're running 1 or 20 parallel browsers, the system dynamically manages resources to ensure stability.
                        </p>
                        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {[
                                'Multi-threaded account verification',
                                'Intelligent wait-times (Custom Jitter)',
                                'Automatic CAPTCHA handling support',
                                'Fingerprint randomization'
                            ].map((item, i) => (
                                <li key={i} className="flex items-center gap-2 text-slate-500 text-xs">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div className="hidden md:block w-px h-32 bg-white/10" />
                    <div className="flex-1 text-center py-6">
                        <div className="inline-block p-4 rounded-3xl bg-accent/5 border border-accent/10 mb-4">
                            <Cpu className="w-12 h-12 text-accent" />
                        </div>
                        <p className="text-slate-300 font-bold mb-1">99.9% Uptime</p>
                        <p className="text-slate-500 text-xs">Platform Reliability</p>
                    </div>
                </div>
            </section>
        </div>
    );
}
