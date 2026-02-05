import React from 'react';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Badge, EmptyState } from '../../components/ui';
import { useUserRoles } from '../../hooks/useApi';

export const RolesPage: React.FC = () => {
  const { data: roles, isLoading, isError, refetch } = useUserRoles();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Roles & Permissions
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          View your assigned roles and permissions
        </p>
      </div>

      <Card>
        <CardHeader
          title="Your Roles"
          description="These roles determine your access level within the platform"
        />

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated">
                <div className="skeleton h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton h-4 w-32" />
                  <div className="skeleton h-3 w-48" />
                </div>
              </div>
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            variant="error"
            title="Failed to load roles"
            description="There was an error loading your roles."
            action={{ label: 'Try Again', onClick: () => refetch() }}
          />
        ) : roles && roles.length > 0 ? (
          <div className="space-y-3">
            {roles.map((role) => (
              <div
                key={role.id}
                className="flex items-center gap-4 p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated border border-light-border dark:border-dark-border"
              >
                <div className="flex-shrink-0 p-2 rounded-full bg-brand-100 dark:bg-brand-900/30">
                  <ShieldCheckIcon className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {role.name}
                  </h3>
                  {role.description && (
                    <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400 truncate">
                      {role.description}
                    </p>
                  )}
                </div>
                {role.external_id && (
                  <Badge variant="neutral" className="flex-shrink-0">
                    ID: {role.external_id}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<ShieldCheckIcon className="h-8 w-8 text-slate-400" />}
            title="No roles assigned"
            description="You don't have any roles assigned yet. Contact an administrator if you need access to specific features."
          />
        )}
      </Card>

      {/* Info card */}
      <Card className="bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800">
        <div className="flex gap-4">
          <div className="flex-shrink-0">
            <ShieldCheckIcon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-brand-900 dark:text-brand-100">
              About Roles
            </h3>
            <p className="mt-1 text-sm text-brand-700 dark:text-brand-300">
              Roles define what actions you can perform within the Atlas platform.
              Your roles are managed by administrators and are synced with the WebAPI
              security system.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
