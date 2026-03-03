'use client';

import { clsx } from 'clsx';

interface SkeletonProps {
    className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
    return (
        <div
            className={clsx(
                'animate-pulse bg-white/5 rounded-md',
                className
            )}
        />
    );
}

export function TableRowSkeleton() {
    return (
        <tr className="border-b border-white/5">
            <td className="px-4 py-4"><Skeleton className="h-4 w-32" /></td>
            <td className="px-4 py-4"><Skeleton className="h-4 w-24" /></td>
            <td className="px-4 py-4"><Skeleton className="h-4 w-12 ml-auto" /></td>
            <td className="px-4 py-4"><Skeleton className="h-6 w-16 rounded-full" /></td>
            <td className="px-4 py-4 hidden md:table-cell"><Skeleton className="h-4 w-48" /></td>
        </tr>
    );
}
