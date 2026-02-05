import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi, adminApi, authApi } from '../lib/api';
import { toast } from '../store/toast';
import type {
  PaginatedResponse,
  User,
  Permission,
  ActivityLog,
  CombinedUser,
  DashboardStats,
  ProfileFormData,
  PasswordChangeFormData,
} from '../types';

// Query keys
export const queryKeys = {
  session: ['session'],
  userProfile: ['user', 'profile'],
  userRoles: ['user', 'roles'],
  userActivity: (params: Record<string, unknown>) => ['user', 'activity', params],
  adminStats: ['admin', 'stats'],
  adminUsers: (params: Record<string, unknown>) => ['admin', 'users', params],
  adminUser: (id: number, type: string) => ['admin', 'user', id, type],
  adminRoles: (params: Record<string, unknown>) => ['admin', 'roles', params],
  adminPermissions: (params: Record<string, unknown>) => ['admin', 'permissions', params],
};

// Session hooks
export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: () => authApi.getSession(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

// User hooks
export function useUserProfile() {
  return useQuery({
    queryKey: queryKeys.userProfile,
    queryFn: () => userApi.getProfile(),
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProfileFormData) => userApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userProfile });
      queryClient.invalidateQueries({ queryKey: queryKeys.session });
      toast.success('Profile updated', 'Your profile has been updated successfully.');
    },
    onError: (error: Error) => {
      toast.error('Update failed', error.message);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: PasswordChangeFormData) => userApi.changePassword(data),
    onSuccess: () => {
      toast.success('Password changed', 'Your password has been updated successfully.');
    },
    onError: (error: Error) => {
      toast.error('Change failed', error.message);
    },
  });
}

export function useUserRoles() {
  return useQuery({
    queryKey: queryKeys.userRoles,
    queryFn: () => userApi.getRoles(),
  });
}

export function useUserActivity(params: {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  ordering?: string;
}) {
  return useQuery<PaginatedResponse<ActivityLog>>({
    queryKey: queryKeys.userActivity(params),
    queryFn: () => userApi.getActivity(params),
    placeholderData: (previousData) => previousData,
  });
}

// Admin hooks
export function useAdminStats() {
  return useQuery<DashboardStats>({
    queryKey: queryKeys.adminStats,
    queryFn: () => adminApi.getStats(),
  });
}

export function useAdminUsers(params: {
  page?: number;
  page_size?: number;
  search?: string;
  user_type?: string;
  status?: string;
  role?: string;
  ordering?: string;
}) {
  return useQuery<PaginatedResponse<CombinedUser>>({
    queryKey: queryKeys.adminUsers(params),
    queryFn: () => adminApi.getUsers(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useAdminUser(id: number, type: 'atlas' | 'admin') {
  return useQuery<CombinedUser>({
    queryKey: queryKeys.adminUser(id, type),
    queryFn: () => adminApi.getUser(id, type),
    enabled: !!id,
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      type,
      data,
    }: {
      id: number;
      type: 'atlas' | 'admin';
      data: { is_disabled?: boolean; permissions?: number[] };
    }) => adminApi.updateUser(id, type, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      toast.success('User updated', 'User has been updated successfully.');
    },
    onError: (error: Error) => {
      toast.error('Update failed', error.message);
    },
  });
}

export function useAdminRoles(params: {
  page?: number;
  page_size?: number;
  search?: string;
  filter?: string;
  ordering?: string;
}) {
  return useQuery<PaginatedResponse<Permission>>({
    queryKey: queryKeys.adminRoles(params),
    queryFn: () => adminApi.getRoles(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useAdminPermissions(params: {
  page?: number;
  page_size?: number;
  search?: string;
  filter?: string;
  ordering?: string;
}) {
  return useQuery<PaginatedResponse<Permission>>({
    queryKey: queryKeys.adminPermissions(params),
    queryFn: () => adminApi.getPermissions(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useBulkGrantPermissions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { user_ids: number[]; permission_ids: number[] }) =>
      adminApi.bulkGrantPermissions(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      toast.success('Permissions granted', `Permissions granted to ${result.updated} users.`);
    },
    onError: (error: Error) => {
      toast.error('Grant failed', error.message);
    },
  });
}

export function usePromoteToAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: number) => adminApi.promoteToAdmin(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.adminStats });
      toast.success('User promoted', 'User has been promoted to admin.');
    },
    onError: (error: Error) => {
      toast.error('Promotion failed', error.message);
    },
  });
}

export function useRemoveAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (adminId: number) => adminApi.removeAdmin(adminId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.adminStats });
      toast.success('Admin removed', 'Admin access has been revoked.');
    },
    onError: (error: Error) => {
      toast.error('Remove failed', error.message);
    },
  });
}

export function useSyncRoles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => adminApi.syncRoles(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'permissions'] });
      toast.success('Roles synced', `Synced ${result.synced} roles from WebAPI.`);
    },
    onError: (error: Error) => {
      toast.error('Sync failed', error.message);
    },
  });
}
