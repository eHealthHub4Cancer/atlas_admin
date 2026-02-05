import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ToastContainer } from './components/ui';
import { useAuthStore } from './store/auth';

// Auth pages
import { LoginPage, SignupPage, AdminLoginPage } from './pages/auth';

// User pages
import {
  UserLayout,
  OverviewPage as UserOverview,
  ProfilePage,
  RolesPage as UserRoles,
  PasswordPage,
  ActivityPage,
  HelpPage,
} from './pages/user';

// Admin pages
import {
  AdminLayout,
  DashboardPage as AdminDashboard,
  UsersPage,
  RolesPage as AdminRoles,
  PermissionsPage,
  BulkRolesPage,
  AdminUsersPage,
} from './pages/admin';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Protected route wrapper
const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  requireAdmin?: boolean;
}> = ({ children, requireAdmin = false }) => {
  const { isAuthenticated, isAdmin, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-light-bg dark:bg-dark-bg">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/user" replace />;
  }

  return <>{children}</>;
};

// Auth route wrapper (redirects if already logged in)
const AuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isAdmin, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-light-bg dark:bg-dark-bg">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to={isAdmin ? '/admin' : '/user'} replace />;
  }

  return <>{children}</>;
};

function App() {
  const { fetchSession } = useAuthStore();

  // Fetch session on mount
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Navigate to="/login" replace />} />

          {/* Auth routes */}
          <Route
            path="/login"
            element={
              <AuthRoute>
                <LoginPage />
              </AuthRoute>
            }
          />
          <Route
            path="/signup"
            element={
              <AuthRoute>
                <SignupPage />
              </AuthRoute>
            }
          />
          <Route
            path="/admin-login"
            element={
              <AuthRoute>
                <AdminLoginPage />
              </AuthRoute>
            }
          />

          {/* User routes */}
          <Route
            path="/user"
            element={
              <ProtectedRoute>
                <UserLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<UserOverview />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="roles" element={<UserRoles />} />
            <Route path="password" element={<PasswordPage />} />
            <Route path="activity" element={<ActivityPage />} />
            <Route path="help" element={<HelpPage />} />
          </Route>

          {/* Admin routes */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminDashboard />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="roles" element={<AdminRoles />} />
            <Route path="permissions" element={<PermissionsPage />} />
            <Route path="bulk-roles" element={<BulkRolesPage />} />
            <Route path="admins" element={<AdminUsersPage />} />
          </Route>

          {/* Catch all - redirect to login */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>

        {/* Toast notifications */}
        <ToastContainer />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
