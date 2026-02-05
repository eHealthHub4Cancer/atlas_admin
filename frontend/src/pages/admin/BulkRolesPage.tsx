import React, { useState } from 'react';
import { CheckIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Button, Badge } from '../../components/ui';
import { useAdminUsers, useAdminPermissions, useBulkGrantPermissions } from '../../hooks';
import { cn } from '../../lib/utils';

export const BulkRolesPage: React.FC = () => {
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);

  const { data: usersData, isLoading: usersLoading } = useAdminUsers({
    page: 1,
    page_size: 100,
    user_type: 'atlas',
    status: 'active',
  });

  const { data: permissionsData, isLoading: permissionsLoading } = useAdminPermissions({
    page: 1,
    page_size: 100,
  });

  const bulkGrant = useBulkGrantPermissions();

  const toggleUser = (userId: number) => {
    setSelectedUsers((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  const togglePermission = (permId: number) => {
    setSelectedPermissions((prev) =>
      prev.includes(permId) ? prev.filter((id) => id !== permId) : [...prev, permId]
    );
  };

  const selectAllUsers = () => {
    if (selectedUsers.length === (usersData?.results.length || 0)) {
      setSelectedUsers([]);
    } else {
      setSelectedUsers(usersData?.results.map((u) => u.id) || []);
    }
  };

  const selectAllPermissions = () => {
    if (selectedPermissions.length === (permissionsData?.results.length || 0)) {
      setSelectedPermissions([]);
    } else {
      setSelectedPermissions(permissionsData?.results.map((p) => p.id) || []);
    }
  };

  const handleSubmit = async () => {
    if (selectedUsers.length === 0 || selectedPermissions.length === 0) return;

    await bulkGrant.mutateAsync({
      user_ids: selectedUsers,
      permission_ids: selectedPermissions,
    });

    setSelectedUsers([]);
    setSelectedPermissions([]);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Bulk Role Assignment
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Assign permissions to multiple users at once
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Users selection */}
        <Card>
          <CardHeader
            title="Select Users"
            description={`${selectedUsers.length} selected`}
            action={
              <Button variant="ghost" size="sm" onClick={selectAllUsers}>
                {selectedUsers.length === (usersData?.results.length || 0)
                  ? 'Deselect All'
                  : 'Select All'}
              </Button>
            }
          />

          {usersLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-12 rounded-xl" />
              ))}
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto space-y-2">
              {usersData?.results.map((user) => (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => toggleUser(user.id)}
                  className={cn(
                    'w-full flex items-center gap-3 p-3 rounded-xl text-left transition-colors',
                    selectedUsers.includes(user.id)
                      ? 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800 border-2'
                      : 'bg-slate-50 dark:bg-dark-elevated border border-transparent hover:border-slate-200 dark:hover:border-slate-700'
                  )}
                >
                  <div
                    className={cn(
                      'flex h-5 w-5 items-center justify-center rounded border transition-colors',
                      selectedUsers.includes(user.id)
                        ? 'bg-brand-500 border-brand-500 text-white'
                        : 'border-slate-300 dark:border-slate-600'
                    )}
                  >
                    {selectedUsers.includes(user.id) && (
                      <CheckIcon className="h-3 w-3" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                      {user.display_name}
                    </div>
                    <div className="text-xs text-slate-500 truncate">
                      {user.email}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>

        {/* Permissions selection */}
        <Card>
          <CardHeader
            title="Select Permissions"
            description={`${selectedPermissions.length} selected`}
            action={
              <Button variant="ghost" size="sm" onClick={selectAllPermissions}>
                {selectedPermissions.length === (permissionsData?.results.length || 0)
                  ? 'Deselect All'
                  : 'Select All'}
              </Button>
            }
          />

          {permissionsLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-12 rounded-xl" />
              ))}
            </div>
          ) : (
            <div className="max-h-96 overflow-y-auto space-y-2">
              {permissionsData?.results.map((perm) => (
                <button
                  key={perm.id}
                  type="button"
                  onClick={() => togglePermission(perm.id)}
                  className={cn(
                    'w-full flex items-center gap-3 p-3 rounded-xl text-left transition-colors',
                    selectedPermissions.includes(perm.id)
                      ? 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800 border-2'
                      : 'bg-slate-50 dark:bg-dark-elevated border border-transparent hover:border-slate-200 dark:hover:border-slate-700'
                  )}
                >
                  <div
                    className={cn(
                      'flex h-5 w-5 items-center justify-center rounded border transition-colors',
                      selectedPermissions.includes(perm.id)
                        ? 'bg-brand-500 border-brand-500 text-white'
                        : 'border-slate-300 dark:border-slate-600'
                    )}
                  >
                    {selectedPermissions.includes(perm.id) && (
                      <CheckIcon className="h-3 w-3" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-900 dark:text-slate-100 truncate">
                      {perm.name}
                    </div>
                    {perm.description && (
                      <div className="text-xs text-slate-500 truncate">
                        {perm.description}
                      </div>
                    )}
                  </div>
                  {perm.external_id && (
                    <Badge variant="neutral" className="text-xs">
                      ID: {perm.external_id}
                    </Badge>
                  )}
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Summary and submit */}
      <Card className="bg-slate-50 dark:bg-dark-elevated">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-brand-100 dark:bg-brand-900/30">
              <UserGroupIcon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-slate-100">
                Ready to assign
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {selectedUsers.length} user(s) × {selectedPermissions.length} permission(s)
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={selectedUsers.length === 0 || selectedPermissions.length === 0}
            isLoading={bulkGrant.isPending}
          >
            Grant Permissions
          </Button>
        </div>
      </Card>
    </div>
  );
};
