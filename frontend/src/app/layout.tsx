'use client';

import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuth, setIsAuth] = useState<boolean | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('reddit_bot_auth_token');
    const authStatus = !!token;
    setIsAuth(authStatus);

    if (!authStatus && pathname !== '/login') {
      router.push('/login');
    } else if (authStatus && pathname === '/login') {
      router.push('/');
    }
  }, [pathname, router]);

  // Prevent flicker before auth check
  if (isAuth === null && pathname !== '/login') {
    return (
      <html lang="en" className={inter.variable}>
        <body className="bg-[#0f172a] antialiased" />
      </html>
    );
  }

  const isLoginPage = pathname === '/login';

  return (
    <html lang="en" className={inter.variable}>
      <body
        className="bg-[#0f172a] text-slate-100 antialiased"
        style={{ fontFamily: 'var(--font-inter), sans-serif' }}
      >
        {isLoginPage ? (
          <main>{children}</main>
        ) : (
          <div className="flex min-h-screen bg-vpn-gradient animate-mesh relative overflow-hidden">
            <Sidebar />
            <main className="flex-1 ml-16 md:ml-56 overflow-y-auto relative z-10">
              {children}
            </main>
          </div>
        )}
      </body>
    </html>
  );
}
