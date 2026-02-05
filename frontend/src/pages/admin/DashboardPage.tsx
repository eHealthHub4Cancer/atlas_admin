import React from 'react';
import { Link } from 'react-router-dom';
import {
  UsersIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  ArrowTrendingUpIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, StatCard, Button } from '../../components/ui';
import { StatCardSkeleton } from '../../components/ui/Skeleton';
import { useAdminStats } from '../../hooks/useApi';

export const DashboardPage: React.FC = () => {
  const { data: stats, isLoading } = useAdminStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Admin Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Platform overview and quick actions
          </p>
        </div>
        <Link to="/admin/users">
          <Button variant="primary" rightIcon={<ArrowRightIcon className="h-4 w-4" />}>
            Manage Users
          </Button>
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Total Users"
              value={stats?.total_users || 0}
              icon={<UsersIcon className="h-6 w-6" />}
            />
            <StatCard
              title="Admin Users"
              value={stats?.admin_users || 0}
              icon={<UserGroupIcon className="h-6 w-6" />}
            />
            <StatCard
              title="Total Roles"
              value={stats?.roles_count || 0}
              icon={<ShieldCheckIcon className="h-6 w-6" />}
            />
            <StatCard
              title="Active Users"
              value={stats?.active_users || 0}
              icon={<ArrowTrendingUpIcon className="h-6 w-6" />}
            />
          </>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="Quick Actions"
            description="Common administrative tasks"
          />
          <div className="grid grid-cols-2 gap-3">
            <Link to="/admin/users">
              <Button variant="secondary" className="w-full justify-start" leftIcon={<UsersIcon className="h-4 w-4" />}>
                View Users
              </Button>
            </Link>
            <Link to="/admin/roles">
              <Button variant="secondary" className="w-full justify-start" leftIcon={<ShieldCheckIcon className="h-4 w-4" />}>
                Manage Roles
              </Button>
            </Link>
            <Link to="/admin/bulk-roles">
              <Button variant="secondary" className="w-full justify-start" leftIcon={<UserGroupIcon className="h-4 w-4" />}>
                Bulk Assign
              </Button>
            </Link>
            <Link to="/admin/permissions">
              <Button variant="secondary" className="w-full justify-start" leftIcon={<ShieldCheckIcon className="h-4 w-4" />}>
                Permissions
              </Button>
            </Link>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="System Status"
            description="Current platform health"
          />
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">WebAPI Connection</span>
              <span className="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Connected
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Database Status</span>
              <span className="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Healthy
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Role Sync</span>
              <span className="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Up to date
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* User breakdown */}
      <Card>
        <CardHeader title="User Breakdown" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="text-center p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated">
            <div className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {stats?.active_users || 0}
            </div>
            <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">Active Users</div>
            <div className="mt-2 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{
                  width: stats?.total_users
                    ? `${((stats.active_users || 0) / stats.total_users) * 100}%`
                    : '0%',
                }}
              />
            </div>
          </div>

          <div className="text-center p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated">
            <div className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {stats?.disabled_users || 0}
            </div>
            <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">Disabled Users</div>
            <div className="mt-2 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-red-500 rounded-full"
                style={{
                  width: stats?.total_users
                    ? `${((stats.disabled_users || 0) / stats.total_users) * 100}%`
                    : '0%',
                }}
              />
            </div>
          </div>

          <div className="text-center p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated">
            <div className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {stats?.admin_users || 0}
            </div>
            <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">Admin Users</div>
            <div className="mt-2 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full"
                style={{
                  width: stats?.total_users
                    ? `${((stats.admin_users || 0) / stats.total_users) * 100}%`
                    : '0%',
                }}
              />
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
