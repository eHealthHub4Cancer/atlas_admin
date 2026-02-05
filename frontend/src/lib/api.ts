import type {
  AuthSession,
  AdminLoginFormData,
  LoginFormData,
  SignupFormData,
  ProfileFormData,
  PasswordChangeFormData,
  PaginatedResponse,
  ActivityLog,
  Permission,
  DashboardStats,
  CombinedUser,
} from '../types';

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

const API_BASE = '/api';

const getCsrfToken = (): string | null => {
  if (typeof document === 'undefined') {
    return null;
  }
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
};

const buildQuery = (params?: Record<string, unknown>): string => {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
};

const parseError = async (response: Response): Promise<Error> => {
  try {
    const data = (await response.json()) as { message?: string; detail?: string; errors?: Record<string, string[]> };
    const message =
      data?.message ||
      data?.detail ||
      (data?.errors
        ? Object.entries(data.errors)
            .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
            .join('\n')
        : response.statusText);
    return new Error(message || 'Request failed');
  } catch {
    return new Error(response.statusText || 'Request failed');
  }
};

const request = async <T>(path: string, options: RequestInit = {}): Promise<T> => {
  const headers = new Headers(options.headers);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  const csrfToken = getCsrfToken();
  if (csrfToken && !headers.has('X-CSRFToken')) {
    headers.set('X-CSRFToken', csrfToken);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
};

export const authApi = {
  getSession: () => request<AuthSession>('/session/'),
  login: (data: LoginFormData) =>
    request<AuthSession>('/login/', { method: 'POST', body: JSON.stringify(data) }),
  adminLogin: (data: AdminLoginFormData) =>
    request<AuthSession>('/admin-login/', { method: 'POST', body: JSON.stringify(data) }),
  signup: (data: SignupFormData) =>
    request<AuthSession>('/signup/', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => request<null>('/logout/', { method: 'POST' }),
};

export const userApi = {
  getProfile: () => request('/user/profile/'),
  updateProfile: (data: ProfileFormData) =>
    request('/user/profile/', { method: 'PUT', body: JSON.stringify(data) }),
  changePassword: (data: PasswordChangeFormData) =>
    request('/user/change-password/', { method: 'POST', body: JSON.stringify(data) }),
  getRoles: () => request<Permission[]>('/user/roles/'),
  getActivity: (params?: Record<string, unknown>) =>
    request<PaginatedResponse<ActivityLog>>(`/user/activity/${buildQuery(params)}`),
};

export const adminApi = {
  getStats: () => request<DashboardStats>('/admin/stats/'),
  getUsers: (params?: Record<string, unknown>) =>
    request<PaginatedResponse<CombinedUser>>(`/admin/users/${buildQuery(params)}`),
  getUser: (id: number, type: 'atlas' | 'admin') =>
    request<CombinedUser>(`/admin/users/${id}/${buildQuery({ type })}`),
  updateUser: (id: number, type: 'atlas' | 'admin', data: JsonValue) =>
    request(`/admin/users/${id}/`, {
      method: 'PUT',
      body: JSON.stringify({ type, ...data }),
    }),
  getRoles: (params?: Record<string, unknown>) =>
    request<PaginatedResponse<Permission>>(`/admin/roles/${buildQuery(params)}`),
  getPermissions: (params?: Record<string, unknown>) =>
    request<PaginatedResponse<Permission>>(`/admin/permissions/${buildQuery(params)}`),
  bulkGrantPermissions: (data: { user_ids: number[]; permission_ids: number[] }) =>
    request<{ updated: number }>('/admin/bulk-grant/', { method: 'POST', body: JSON.stringify(data) }),
  promoteToAdmin: (userId: number) =>
    request('/admin/promote/', { method: 'POST', body: JSON.stringify({ user_id: userId }) }),
  removeAdmin: (adminId: number) =>
    request('/admin/remove-admin/', { method: 'POST', body: JSON.stringify({ admin_id: adminId }) }),
  syncRoles: () => request<{ synced: number }>('/admin/sync-roles/', { method: 'POST' }),
};
