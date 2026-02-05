import React, { useState } from 'react';
import { ShieldExclamationIcon, UserPlusIcon, UserMinusIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Button, Badge, ConfirmDialog } from '../../components/ui';
import { useAdminUsers, usePromoteToAdmin, useRemoveAdmin } from '../../hooks';
import { cn } from '../../lib/utils';

export const AdminUsersPage: React.FC = () => {
  const [confirmPromote, setConfirmPromote] = useState<number | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<number | null>(null);

  // Get atlas users with email (eligible for promotion)
  const { data: atlasUsers, isLoading: atlasLoading } = useAdminUsers({
    page: 1,
    page_size: 100,
    user_type: 'atlas',
    status: 'active',
  });

  // Get current admin users
  const { data: adminUsers, isLoading: adminLoading } = useAdminUsers({
    page: 1,
    page_size: 100,
    user_type: 'admin',
  });

  const promoteToAdmin = usePromoteToAdmin();
  const removeAdmin = useRemoveAdmin();

  const eligibleForPromotion = atlasUsers?.results.filter((u) => u.email) || [];
  const currentAdmins = adminUsers?.results || [];

  const handlePromote = async () => {
    if (confirmPromote === null) return;
    await promoteToAdmin.mutateAsync(confirmPromote);
    setConfirmPromote(null);
  };

  const handleRemove = async () => {
    if (confirmRemove === null) return;
    await removeAdmin.mutateAsync(confirmRemove);
    setConfirmRemove(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Admin User Management
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Promote users to admin or revoke admin access
        </p>
      </div>

      {/* Warning banner */}
      <Card className="bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800">
        <div className="flex gap-4">
          <ShieldExclamationIcon className="h-6 w-6 text-amber-600 dark:text-amber-400 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-medium text-amber-900 dark:text-amber-100">
              Super Admin Only
            </h3>
            <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
              These actions are restricted to super administrators. Changes affect
              administrative access to the platform.
            </p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Promote to Admin */}
        <Card>
          <CardHeader
            title="Promote to Admin"
            description="Select users to grant admin access"
          />

          {atlasLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton h-16 rounded-xl" />
              ))}
            </div>
          ) : eligibleForPromotion.length === 0 ? (
            <div className="text-center py-8">
              <UserPlusIcon className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No eligible users found
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                Users must have an email to be promoted
              </p>
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto space-y-2">
              {eligibleForPromotion.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-dark-elevated"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 font-medium">
                      {user.display_name?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <div className="font-medium text-slate-900 dark:text-slate-100">
                        {user.display_name}
                      </div>
                      <div className="text-xs text-slate-500">{user.email}</div>
                    </div>
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setConfirmPromote(user.id)}
                    leftIcon={<UserPlusIcon className="h-4 w-4" />}
                  >
                    Promote
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Current Admins */}
        <Card>
          <CardHeader
            title="Current Admins"
            description="Manage existing admin accounts"
          />

          {adminLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton h-16 rounded-xl" />
              ))}
            </div>
          ) : currentAdmins.length === 0 ? (
            <div className="text-center py-8">
              <ShieldExclamationIcon className="h-12 w-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No admin users found
              </p>
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto space-y-2">
              {currentAdmins.map((admin) => (
                <div
                  key={admin.id}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-xl',
                    admin.is_super_admin
                      ? 'bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800'
                      : 'bg-slate-50 dark:bg-dark-elevated'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-full font-medium',
                        admin.is_super_admin
                          ? 'bg-brand-500 text-white'
                          : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                      )}
                    >
                      {admin.display_name?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {admin.display_name}
                        </span>
                        {admin.is_super_admin && (
                          <Badge variant="primary">Super Admin</Badge>
                        )}
                      </div>
                      <div className="text-xs text-slate-500">{admin.email}</div>
                    </div>
                  </div>
                  {!admin.is_super_admin && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setConfirmRemove(admin.id)}
                      leftIcon={<UserMinusIcon className="h-4 w-4" />}
                    >
                      Remove
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Confirm Promote Dialog */}
      <ConfirmDialog
        isOpen={confirmPromote !== null}
        onClose={() => setConfirmPromote(null)}
        onConfirm={handlePromote}
        title="Promote to Admin"
        message="Are you sure you want to grant admin access to this user? They will be able to manage other users and permissions."
        confirmText="Promote"
        variant="warning"
        isLoading={promoteToAdmin.isPending}
      />

      {/* Confirm Remove Dialog */}
      <ConfirmDialog
        isOpen={confirmRemove !== null}
        onClose={() => setConfirmRemove(null)}
        onConfirm={handleRemove}
        title="Remove Admin Access"
        message="Are you sure you want to revoke admin access from this user? They will no longer be able to access the admin console."
        confirmText="Remove"
        variant="danger"
        isLoading={removeAdmin.isPending}
      />
    </div>
  );
};
