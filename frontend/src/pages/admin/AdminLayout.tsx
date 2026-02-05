import React from 'react';
import { Outlet } from 'react-router-dom';
import {
  ChartBarIcon,
  UsersIcon,
  ShieldCheckIcon,
  KeyIcon,
  UserGroupIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';
import { DashboardLayout } from '../../components/layout';
import type { NavItem } from '../../components/layout';
import { useAuthStore } from '../../store/auth';

export const AdminLayout: React.FC = () => {
  const { session } = useAuthStore();
  const isSuperAdmin = session?.is_super_admin;

  const navigation: NavItem[] = [
    { name: 'Dashboard', href: '/admin', icon: ChartBarIcon },
    { name: 'Users', href: '/admin/users', icon: UsersIcon },
    { name: 'Roles', href: '/admin/roles', icon: ShieldCheckIcon },
    { name: 'Permissions', href: '/admin/permissions', icon: KeyIcon },
    { name: 'Bulk Assign', href: '/admin/bulk-roles', icon: UserGroupIcon },
    ...(isSuperAdmin
      ? [{ name: 'Admin Users', href: '/admin/admins', icon: UserPlusIcon }]
      : []),
  ];

  return (
    <DashboardLayout
      navigation={navigation}
      title="Atlas"
      subtitle="Admin Console"
      logo={
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-purple-500 text-white font-bold text-lg shadow-glow-sm">
          A
        </div>
      }
    >
      <Outlet />
    </DashboardLayout>
  );
};
