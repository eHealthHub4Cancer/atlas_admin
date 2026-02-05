import React from 'react';
import { Outlet } from 'react-router-dom';
import {
  HomeIcon,
  UserCircleIcon,
  KeyIcon,
  ShieldCheckIcon,
  ClockIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/outline';
import { DashboardLayout } from '../../components/layout';
import type { NavItem } from '../../components/layout';

const navigation: NavItem[] = [
  { name: 'Overview', href: '/user', icon: HomeIcon },
  { name: 'Profile', href: '/user/profile', icon: UserCircleIcon },
  { name: 'Roles & Permissions', href: '/user/roles', icon: ShieldCheckIcon },
  { name: 'Change Password', href: '/user/password', icon: KeyIcon },
  { name: 'Activity Log', href: '/user/activity', icon: ClockIcon },
  { name: 'Help', href: '/user/help', icon: QuestionMarkCircleIcon },
];

export const UserLayout: React.FC = () => {
  return (
    <DashboardLayout
      navigation={navigation}
      title="Atlas"
      subtitle="User Dashboard"
    >
      <Outlet />
    </DashboardLayout>
  );
};
