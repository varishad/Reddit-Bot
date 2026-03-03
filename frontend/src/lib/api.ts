import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Shorter timeout so errors surface quickly instead of hanging
const api = axios.create({
    baseURL: API_BASE,
    timeout: 8000, // 8s max — prevents indefinite hang on cold start
    headers: { 'Content-Type': 'application/json' },
});

// Interceptor: inject auth token
api.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('reddit_bot_auth_token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    return config;
});

// ─── Retry helper ──────────────────────────────────────────────────────────
// Retries a request up to `retries` times with exponential backoff.
// Used for the startup health probe so the UI waits gracefully.
async function withRetry<T>(
    fn: () => Promise<T>,
    retries = 3,
    delayMs = 800
): Promise<T> {
    let lastError: unknown;
    for (let i = 0; i < retries; i++) {
        try {
            return await fn();
        } catch (e) {
            lastError = e;
            if (i < retries - 1) {
                await new Promise(r => setTimeout(r, delayMs * (i + 1)));
            }
        }
    }
    throw lastError;
}

// ─── Backend readiness probe ────────────────────────────────────────────────
// Polls /health until the backend responds or timeout is reached.
// Call this before making any authenticated requests on startup.
export async function waitForBackend(maxWaitMs = 15000): Promise<boolean> {
    const deadline = Date.now() + maxWaitMs;
    while (Date.now() < deadline) {
        try {
            await api.get('/health', { timeout: 1500 });
            return true;
        } catch {
            await new Promise(r => setTimeout(r, 600));
        }
    }
    return false;
}

// ─── Interfaces ────────────────────────────────────────────────────────────
export interface BotStats {
    total: number;
    success: number;
    invalid: number;
    banned: number;
    error: number;
    vpn_rotations: number;
    uptime_seconds: number;
    start_time: string | null;
}

export interface LogEntry {
    timestamp: string;
    message: string;
    type: 'info' | 'success' | 'error' | 'warning';
}

export interface BotStatus {
    is_running: boolean;
    session_id: string | null;
    vpn_location?: string;
    stats: BotStats;
    recent_logs: LogEntry[];
}

// ─── API surface ────────────────────────────────────────────────────────────
export const botApi = {
    health: () => api.get('/health'),
    getSavedCredentials: () => withRetry(() => api.get('/auth/saved-credentials'), 2, 500),
    login: async (license_key: string, password: string) => {
        const response = await withRetry(() => api.post('/auth/login', { license_key, password }), 2, 600);
        if (response.data.status === 'success') {
            localStorage.setItem('reddit_bot_auth_token', license_key);
        }
        return response;
    },
    logout: async () => {
        try {
            await api.post('/auth/logout');
        } catch {
            // Backend may already be down — ignore
        }
        localStorage.removeItem('reddit_bot_auth_token');
        window.location.href = '/login';
    },
    start: (file_path?: string, parallel_browsers?: number) =>
        api.post('/bot/start', null, { params: { file_path, parallel_browsers } }),
    uploadCredentials: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/bot/upload-credentials', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    pasteCredentials: (text: string) => api.post('/bot/paste-credentials', { text }),
    stop: () => api.post('/bot/stop'),
    userInfo: () => api.get('/user/info'),
    updateUsername: (username: string) => api.post('/user/update-username', { username }),
    getSettings: () => api.get('/bot/settings'),
    updateSettings: (settings: unknown) => api.post('/bot/settings', settings),
    results: () => api.get('/accounts/results'),
    status: (): Promise<{ data: BotStatus }> => api.get('/bot/status'),
    logs: (): Promise<{ data: LogEntry[] }> => api.get('/bot/full-logs'),

    // Admin
    getUsers: () => api.get('/admin/users'),
    resetPassword: (license_key: string, new_password: string) =>
        api.post('/admin/reset-password', { license_key, new_password }),
    createUser: (userData: unknown) => api.post('/admin/create-user', userData),
};
