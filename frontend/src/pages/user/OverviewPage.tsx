import React from 'react';
import { Link } from 'react-router-dom';
import {
  UserCircleIcon,
  ShieldCheckIcon,
  ClockIcon,
  ArrowRightIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, StatCard, Badge, Button } from '../../components/ui';
import { StatCardSkeleton } from '../../components/ui/Skeleton';
import { useUserProfile, useUserRoles } from '../../hooks/useApi';
import { formatRelativeTime, capitalize } from '../../lib/utils';

export const OverviewPage: React.FC = () => {
  const { data: profile, isLoading: profileLoading } = useUserProfile();
  const { data: roles, isLoading: rolesLoading } = useUserRoles();

  // Calculate profile completion
  const calculateCompletion = () => {
    if (!profile) return 0;
    const fields = ['username', 'profile.display_name', 'profile.email', 'profile.affiliation', 'profile.prefix'];
    let completed = 0;

    if (profile.username) completed++;
    if (profile.profile?.display_name) completed++;
    if (profile.profile?.email) completed++;
    if (profile.profile?.affiliation) completed++;
    if (profile.profile?.prefix) completed++;

    return Math.round((completed / fields.length) * 100);
  };

  const completion = calculateCompletion();
  const missingFields: string[] = [];

  if (profile) {
    if (!profile.profile?.affiliation) missingFields.push('Affiliation');
    if (!profile.profile?.prefix) missingFields.push('Prefix');
  }

  return (
    <div className="space-y-6">
      {/* Welcome header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Welcome back{profile?.profile?.display_name ? `, ${profile.profile.display_name}` : ''}!
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Here's an overview of your account
          </p>
        </div>
        <Link to="/user/profile">
          <Button variant="secondary" rightIcon={<ArrowRightIcon className="h-4 w-4" />}>
            Edit Profile
          </Button>
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {profileLoading ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : (
          <>
            <StatCard
              title="Profile Completion"
              value={`${completion}%`}
              icon={<UserCircleIcon className="h-6 w-6" />}
            />
            <StatCard
              title="Roles Assigned"
              value={roles?.length || 0}
              icon={<ShieldCheckIcon className="h-6 w-6" />}
            />
            <StatCard
              title="Account Status"
              value={profile?.is_disabled ? 'Disabled' : 'Active'}
              icon={<ClockIcon className="h-6 w-6" />}
            />
          </>
        )}
      </div>

      {/* Profile completion warning */}
      {completion < 100 && missingFields.length > 0 && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <ExclamationTriangleIcon className="h-6 w-6 text-amber-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Complete Your Profile
              </h3>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                Your profile is {completion}% complete. Add the following to complete it:
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {missingFields.map((field) => (
                  <Badge key={field} variant="warning">
                    {field}
                  </Badge>
                ))}
              </div>
              <div className="mt-3">
                <Link to="/user/profile">
                  <Button variant="primary" size="sm">
                    Complete Profile
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Quick info cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Account info */}
        <Card>
          <CardHeader
            title="Account Information"
            action={
              <Link to="/user/profile">
                <Button variant="ghost" size="sm">
                  View Details
                </Button>
              </Link>
            }
          />
          {profileLoading ? (
            <div className="space-y-3">
              <div className="skeleton h-5 w-3/4" />
              <div className="skeleton h-5 w-1/2" />
              <div className="skeleton h-5 w-2/3" />
            </div>
          ) : (
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-slate-500 dark:text-slate-400">Display Name</dt>
                <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {profile?.profile?.display_name || '-'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-slate-500 dark:text-slate-400">Username</dt>
                <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {profile?.username}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-slate-500 dark:text-slate-400">Email</dt>
                <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {profile?.profile?.email || '-'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-slate-500 dark:text-slate-400">Role</dt>
                <dd>
                  <Badge variant="primary">{capitalize(profile?.role || 'guest')}</Badge>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-slate-500 dark:text-slate-400">Member Since</dt>
                <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {profile?.created_at ? formatRelativeTime(profile.created_at) : '-'}
                </dd>
              </div>
            </dl>
          )}
        </Card>

        {/* Roles preview */}
        <Card>
          <CardHeader
            title="Your Roles"
            action={
              <Link to="/user/roles">
                <Button variant="ghost" size="sm">
                  View All
                </Button>
              </Link>
            }
          />
          {rolesLoading ? (
            <div className="space-y-2">
              <div className="skeleton h-8 w-24" />
              <div className="skeleton h-8 w-32" />
              <div className="skeleton h-8 w-28" />
            </div>
          ) : roles && roles.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {roles.slice(0, 6).map((role) => (
                <Badge key={role.id} variant="primary">
                  {role.name}
                </Badge>
              ))}
              {roles.length > 6 && (
                <Badge variant="neutral">+{roles.length - 6} more</Badge>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No roles assigned yet.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
};
