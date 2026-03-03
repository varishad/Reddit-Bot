import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE,
    headers: { 'Content-Type': 'application/json' },
});

// Interceptor to add auth token (license_key) to requests
api.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('reddit_bot_auth_token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    return config;
});

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

export const botApi = {
    health: () => api.get('/health'),
    login: async (license_key: string, password: string) => {
        const response = await api.post('/auth/login', { license_key, password });
        if (response.data.status === 'success') {
            localStorage.setItem('reddit_bot_auth_token', license_key);
        }
        return response;
    },
    logout: () => {
        localStorage.removeItem('reddit_bot_auth_token');
        window.location.href = '/login';
    },
    start: (file_path?: string, parallel_browsers?: number) =>
        api.post('/bot/start', null, { params: { file_path, parallel_browsers } }),
    uploadCredentials: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/bot/upload-credentials', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    },
    pasteCredentials: (text: string) => api.post('/bot/paste-credentials', { text }),
    stop: () => api.post('/bot/stop'),
    userInfo: () => api.get('/user/info'),
    updateUsername: (username: string) => api.post('/user/update-username', { username }),
    results: () => api.get('/accounts/results'),
    status: (): Promise<{ data: BotStatus }> => api.get('/bot/status'),
    logs: (): Promise<{ data: LogEntry[] }> => api.get('/bot/full-logs'),

    // Admin
    getUsers: () => api.get('/admin/users'),
    resetPassword: (license_key: string, new_password: string) =>
        api.post('/admin/reset-password', { license_key, new_password }),
    createUser: (userData: any) =>
        api.post('/admin/create-user', userData),
};
