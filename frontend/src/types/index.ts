// User types
export interface User {
  id: number;
  username: string;
  role: 'researcher' | 'guest' | 'student';
  is_disabled: boolean;
  created_at: string;
  updated_at: string;
  profile?: UserProfile;
  permissions: Permission[];
}

export interface UserProfile {
  id: number;
  display_name: string;
  email: string;
  affiliation?: string;
  prefix?: string;
  created_at: string;
  updated_at: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  affiliation?: string;
  is_admin: boolean;
  is_super_admin: boolean;
}

export interface Permission {
  id: number;
  name: string;
  external_id?: number;
  description?: string;
}

// API Response types
export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  message: string;
  errors?: Record<string, string[]>;
}

// Table types
export interface TableColumn<T> {
  id: string;
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  sortable?: boolean;
  className?: string;
}

export interface TableFilters {
  search?: string;
  status?: string;
  role?: string;
  date_from?: string;
  date_to?: string;
  [key: string]: string | undefined;
}

export interface TableState {
  page: number;
  page_size: number;
  ordering?: string;
  filters: TableFilters;
}

// Activity log
export interface ActivityLog {
  id: number;
  action: string;
  summary: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error' | 'info';
}

// Auth session
export interface AuthSession {
  user_id: number;
  username: string;
  role: string;
  is_admin: boolean;
  is_super_admin: boolean;
  display_name?: string;
  email?: string;
}

// Form types
export interface LoginFormData {
  username: string;
  password: string;
}

export interface SignupFormData {
  username: string;
  display_name: string;
  email: string;
  affiliation?: string;
  prefix: string;
  role: string;
  password1: string;
  password2: string;
}

export interface ProfileFormData {
  display_name: string;
  email: string;
  affiliation?: string;
  prefix?: string;
}

export interface PasswordChangeFormData {
  current_password: string;
  new_password1: string;
  new_password2: string;
}

// Stats
export interface DashboardStats {
  total_users: number;
  admin_users: number;
  roles_count: number;
  active_users: number;
  disabled_users: number;
}

// Combined user for admin view
export interface CombinedUser {
  id: number;
  username?: string;
  display_name: string;
  email: string;
  role: string;
  is_disabled: boolean;
  is_admin: boolean;
  is_super_admin: boolean;
  user_type: 'atlas' | 'admin';
  permissions: Permission[];
}
