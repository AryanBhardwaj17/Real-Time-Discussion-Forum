import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,  // Send HttpOnly cookies with every request
});

// ── Response interceptor: auto-refresh on 401 ───────────────────────
let refreshPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    // Auto-refresh on 401 (expired token) or 403 (stale role in JWT)
    if ((status === 401 || status === 403) && !original._retry) {
      original._retry = true;

      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
          .then(() => true)
          .catch(() => false)
          .finally(() => {
            refreshPromise = null;
          });
      }

      const success = await refreshPromise;
      if (success) {
        return api(original);
      }
    }

    return Promise.reject(error);
  }
);

// ── Auth ────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  refreshToken: () => axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true }),
  changePassword: (data) => api.post('/auth/change-password', data),
};

// ── Users ───────────────────────────────────────────────────────────
export const usersAPI = {
  getMe: () => api.get('/users/me'),
  updateMe: (data) => api.patch('/users/me', data),
  deactivateMe: () => api.patch('/users/me/deactivate'),
  deleteMe: () => api.delete('/users/me'),
  getPublicProfile: (username) => api.get(`/users/${encodeURIComponent(username)}`),
};

// ── Public Profiles (content service) ───────────────────────────────
export const profilesAPI = {
  threads: (userId, params) => api.get(`/profiles/${userId}/threads`, { params }),
  stats: (userId) => api.get(`/profiles/${userId}/stats`),
};

// ── Threads ─────────────────────────────────────────────────────────
export const threadsAPI = {
  list: (params) => api.get('/threads', { params }),
  get: (id) => api.get(`/threads/${id}`),
  create: (data) => api.post('/threads', data),
  update: (id, data) => api.patch(`/threads/${id}`, data),
  delete: (id) => api.delete(`/threads/${id}`),
  toggleLike: (id) => api.post(`/threads/${id}/like`),
  likeStatus: (id) => api.get(`/threads/${id}/like/status`),
  likers: (id, params) => api.get(`/threads/${id}/likers`, { params }),
  report: (id, data) => api.post(`/threads/${id}/report`, data),
  togglePin: (id) => api.post(`/threads/${id}/pin`),
  toggleLock: (id) => api.post(`/threads/${id}/lock`),
};

// ── Comments ────────────────────────────────────────────────────────
export const commentsAPI = {
  list: (threadId, params) => api.get(`/threads/${threadId}/comments`, { params }),
  create: (threadId, data) => api.post(`/threads/${threadId}/comments`, data),
  replies: (commentId, params) => api.get(`/comments/${commentId}/replies`, { params }),
  update: (id, data) => api.patch(`/comments/${id}`, data),
  delete: (id) => api.delete(`/comments/${id}`),
  toggleLike: (id) => api.post(`/comments/${id}/like`),
  likeStatus: (id) => api.get(`/comments/${id}/like/status`),
  likers: (id, params) => api.get(`/comments/${id}/likers`, { params }),
  report: (id, data) => api.post(`/comments/${id}/report`, data),
};

// ── Notifications ───────────────────────────────────────────────────
export const notificationsAPI = {
  list: (params) => api.get('/notifications', { params }),
  unreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
};

// ── Search ──────────────────────────────────────────────────────────
export const searchAPI = {
  threads: (params) => api.get('/search/threads', { params }),
};

// ── Dashboard ───────────────────────────────────────────────────────
export const dashboardAPI = {
  adminStats: () => api.get('/dashboard/admin/stats'),
  auditLog: (params) => api.get('/dashboard/admin/audit-log', { params }),
  modActivity: (params) => api.get('/dashboard/mod/activity', { params }),
  myThreads: (params) => api.get('/dashboard/me/threads', { params }),
  myComments: (params) => api.get('/dashboard/me/comments', { params }),
  myStats: () => api.get('/dashboard/me/stats'),
};

// ── Admin ───────────────────────────────────────────────────────────
export const adminAPI = {
  listUsers: (params) => api.get('/admin/users', { params }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  updateRole: (id, role) => api.patch(`/admin/users/${id}/role`, { role }),
  deactivate: (id) => api.post(`/admin/users/${id}/deactivate`),
  reactivate: (id) => api.post(`/admin/users/${id}/reactivate`),
};

// ── Reports ─────────────────────────────────────────────────────────
export const reportsAPI = {
  list: (params) => api.get('/reports', { params }),
  resolve: (id, action) => api.post(`/reports/${id}/resolve`, { action }),
};

export default api;
