'use client';

import { motion } from 'framer-motion';
import { Power } from 'lucide-react';
import { clsx } from 'clsx';

interface PowerButtonProps {
    isRunning: boolean;
    onClick: () => void;
    disabled?: boolean;
}

export function PowerButton({ isRunning, onClick, disabled }: PowerButtonProps) {
    return (
        <div className="flex flex-col items-center gap-4">
            {/* Outer glow ring */}
            <div className="relative">
                <motion.div
                    className={clsx(
                        'absolute inset-0 rounded-full blur-2xl opacity-40',
                        isRunning ? 'bg-emerald-500' : 'bg-rose-500'
                    )}
                    animate={{ scale: isRunning ? [1, 1.2, 1] : 1, opacity: isRunning ? [0.4, 0.6, 0.4] : 0.3 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                />

                {/* Button */}
                <motion.button
                    onClick={disabled ? undefined : onClick}
                    whileTap={{ scale: 0.95 }}
                    whileHover={{ scale: 1.05 }}
                    disabled={disabled}
                    className={clsx(
                        'relative w-36 h-36 rounded-full flex items-center justify-center cursor-pointer transition-all duration-500 border-4 shadow-2xl focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed',
                        isRunning
                            ? 'bg-gradient-to-br from-emerald-500 to-teal-600 border-emerald-400/50 shadow-emerald-500/30'
                            : 'bg-gradient-to-br from-rose-500 to-red-700 border-rose-400/50 shadow-rose-500/30'
                    )}
                >
                    <Power className="w-14 h-14 text-white drop-shadow-lg" strokeWidth={1.8} />
                </motion.button>
            </div>

            {/* Status label */}
            <motion.div
                key={isRunning ? 'on' : 'off'}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2"
            >
                <div
                    className={clsx(
                        'w-2.5 h-2.5 rounded-full',
                        isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                    )}
                />
                <span className={clsx('text-sm font-semibold', isRunning ? 'text-emerald-400' : 'text-slate-500')}>
                    {isRunning ? 'Bot Running' : 'Bot Stopped'}
                </span>
            </motion.div>
        </div>
    );
}
