'use client';

import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { botApi, waitForBackend } from '@/lib/api';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuth, setIsAuth] = useState<boolean | null>(null);
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      // ── Step 1: Check local token first (instant, no network) ──────────
      const existingToken = localStorage.getItem('reddit_bot_auth_token');

      // ── Step 2: Wait for backend to be ready before any API calls ───────
      // This prevents the Axios Network Error on cold start.
      const ready = await waitForBackend(15000);
      setBackendReady(ready);

      if (!ready) {
        // Backend never came up — fall through to login page
        setIsAuth(false);
        if (pathname !== '/login') router.push('/login');
        return;
      }

      // ── Step 3: If already have token, we're done ─────────────────────
      if (existingToken) {
        setIsAuth(true);
        if (pathname === '/login') router.push('/');
        return;
      }

      // ── Step 4: Try auto-login with saved credentials ─────────────────
      try {
        const { data: saved } = await botApi.getSavedCredentials();
        if (saved?.license_key && saved?.password) {
          const loginRes = await botApi.login(saved.license_key, saved.password);
          if (loginRes.data.status === 'success') {
            setIsAuth(true);
            if (pathname === '/login') router.push('/');
            return;
          }
        }
      } catch {
        // Saved credentials absent or invalid — continue to login
      }

      setIsAuth(false);
      if (pathname !== '/login') router.push('/login');
    };

    checkAuth();
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
        className="antialiased"
        style={{
          fontFamily: 'var(--font-inter), sans-serif',
          /* Base layer — darkest, this is the "floor" the sidebar floats on */
          background: '#0d1424',
          color: '#f8fafc',
        }}
      >
        {isLoginPage ? (
          <main>{children}</main>
        ) : (
          <div className="flex min-h-screen">
            {/* Sidebar sits at base dark level — NO background of its own */}
            <Sidebar />
            <main
              className="flex-1 ml-[262px] overflow-y-auto relative"
              style={{
                background: '#111827',
                minHeight: '100vh',
              }}
            >
              {children}
            </main>
          </div>
        )}
      </body>
    </html>
  );
}
