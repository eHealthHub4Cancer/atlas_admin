import React, { useMemo, useState } from 'react';
import { type ColumnDef } from '@tanstack/react-table';
import { PencilIcon, EyeIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Badge, Button, Modal, ModalFooter, Input } from '../../components/ui';
import { DataTable, Pagination, FilterBar, type FilterConfig } from '../../components/data-table';
import { useTableState, useAdminUsers, useUpdateUser } from '../../hooks';
import { capitalize } from '../../lib/utils';
import type { CombinedUser } from '../../types';

const userTypeOptions = [
  { value: 'atlas', label: 'Atlas Users' },
  { value: 'admin', label: 'Admin Users' },
];

const statusOptions = [
  { value: 'active', label: 'Active' },
  { value: 'disabled', label: 'Disabled' },
];

const roleOptions = [
  { value: 'researcher', label: 'Researcher' },
  { value: 'guest', label: 'Guest' },
  { value: 'student', label: 'Student' },
];

const filters: FilterConfig[] = [
  {
    key: 'user_type',
    label: 'User Type',
    type: 'select',
    options: userTypeOptions,
    placeholder: 'All types',
  },
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: statusOptions,
    placeholder: 'All statuses',
  },
  {
    key: 'role',
    label: 'Role',
    type: 'select',
    options: roleOptions,
    placeholder: 'All roles',
  },
];

export const UsersPage: React.FC = () => {
  const tableState = useTableState({
    defaultPageSize: 10,
    syncWithUrl: true,
    filterKeys: ['user_type', 'status', 'role'],
  });

  const { data, isLoading, isError, refetch } = useAdminUsers({
    page: tableState.page,
    page_size: tableState.pageSize,
    search: tableState.search,
    user_type: tableState.filters.user_type,
    status: tableState.filters.status,
    role: tableState.filters.role,
    ordering: tableState.sorting.length > 0
      ? (tableState.sorting[0].desc ? '-' : '') + tableState.sorting[0].id
      : undefined,
  });

  const updateUser = useUpdateUser();
  const [selectedUser, setSelectedUser] = useState<CombinedUser | null>(null);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);

  const handleView = (user: CombinedUser) => {
    setSelectedUser(user);
    setViewModalOpen(true);
  };

  const handleEdit = (user: CombinedUser) => {
    setSelectedUser(user);
    setEditModalOpen(true);
  };

  const handleToggleDisabled = async () => {
    if (!selectedUser) return;
    await updateUser.mutateAsync({
      id: selectedUser.id,
      type: selectedUser.user_type,
      data: { is_disabled: !selectedUser.is_disabled },
    });
    setEditModalOpen(false);
  };

  const columns: ColumnDef<CombinedUser>[] = useMemo(
    () => [
      {
        id: 'display_name',
        header: 'Name',
        accessorKey: 'display_name',
        enableSorting: true,
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-sm font-medium">
              {row.original.display_name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div>
              <div className="font-medium text-slate-900 dark:text-slate-100">
                {row.original.display_name}
              </div>
              {row.original.username && (
                <div className="text-xs text-slate-500">@{row.original.username}</div>
              )}
            </div>
          </div>
        ),
      },
      {
        id: 'email',
        header: 'Email',
        accessorKey: 'email',
        enableSorting: true,
      },
      {
        id: 'role',
        header: 'Role',
        accessorKey: 'role',
        enableSorting: true,
        cell: ({ row }) => (
          <Badge variant="primary">{capitalize(row.original.role)}</Badge>
        ),
      },
      {
        id: 'user_type',
        header: 'Type',
        accessorKey: 'user_type',
        cell: ({ row }) => (
          <Badge variant={row.original.user_type === 'admin' ? 'warning' : 'neutral'}>
            {row.original.user_type === 'admin' ? 'Admin' : 'Atlas'}
          </Badge>
        ),
      },
      {
        id: 'is_disabled',
        header: 'Status',
        accessorKey: 'is_disabled',
        enableSorting: true,
        cell: ({ row }) => (
          <Badge variant={row.original.is_disabled ? 'danger' : 'success'} dot>
            {row.original.is_disabled ? 'Disabled' : 'Active'}
          </Badge>
        ),
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <div className="flex items-center gap-1 justify-end">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleView(row.original)}
              aria-label="View user"
            >
              <EyeIcon className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleEdit(row.original)}
              aria-label="Edit user"
            >
              <PencilIcon className="h-4 w-4" />
            </Button>
          </div>
        ),
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          User Management
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          View and manage all platform users
        </p>
      </div>

      <Card>
        <CardHeader
          title="All Users"
          description="Combined view of Atlas and Admin users"
        />

        <FilterBar
          searchValue={tableState.search}
          onSearchChange={tableState.setSearch}
          filters={filters}
          filterValues={tableState.filters}
          onFilterChange={tableState.setFilter}
          onClearFilters={tableState.clearFilters}
          placeholder="Search by name, email, or username..."
          className="mb-4"
        />

        <DataTable
          data={data?.results || []}
          columns={columns}
          isLoading={isLoading}
          isError={isError}
          sorting={tableState.sorting}
          onSortingChange={tableState.setSorting}
          searchQuery={tableState.search}
          onClearSearch={() => tableState.setSearch('')}
          onRetry={refetch}
          emptyMessage="No users found"
        />

        {data && data.total_pages > 0 && (
          <Pagination
            page={tableState.page}
            pageSize={tableState.pageSize}
            totalCount={data.count}
            totalPages={data.total_pages}
            onPageChange={tableState.setPage}
            onPageSizeChange={tableState.setPageSize}
            isLoading={isLoading}
          />
        )}
      </Card>

      {/* View Modal */}
      <Modal
        isOpen={viewModalOpen}
        onClose={() => setViewModalOpen(false)}
        title="User Details"
        size="md"
      >
        {selectedUser && (
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-2xl font-bold">
                {selectedUser.display_name?.charAt(0)?.toUpperCase() || '?'}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {selectedUser.display_name}
                </h3>
                <p className="text-sm text-slate-500">{selectedUser.email}</p>
              </div>
            </div>

            <dl className="grid grid-cols-2 gap-4">
              {selectedUser.username && (
                <div>
                  <dt className="text-sm text-slate-500 dark:text-slate-400">Username</dt>
                  <dd className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    @{selectedUser.username}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-sm text-slate-500 dark:text-slate-400">Role</dt>
                <dd>
                  <Badge variant="primary">{capitalize(selectedUser.role)}</Badge>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500 dark:text-slate-400">User Type</dt>
                <dd>
                  <Badge variant={selectedUser.user_type === 'admin' ? 'warning' : 'neutral'}>
                    {selectedUser.user_type === 'admin' ? 'Admin User' : 'Atlas User'}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-500 dark:text-slate-400">Status</dt>
                <dd>
                  <Badge variant={selectedUser.is_disabled ? 'danger' : 'success'} dot>
                    {selectedUser.is_disabled ? 'Disabled' : 'Active'}
                  </Badge>
                </dd>
              </div>
            </dl>

            {selectedUser.permissions && selectedUser.permissions.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Permissions ({selectedUser.permissions.length})
                </h4>
                <div className="flex flex-wrap gap-1">
                  {selectedUser.permissions.slice(0, 10).map((perm) => (
                    <Badge key={perm.id} variant="neutral" className="text-xs">
                      {perm.name}
                    </Badge>
                  ))}
                  {selectedUser.permissions.length > 10 && (
                    <Badge variant="neutral" className="text-xs">
                      +{selectedUser.permissions.length - 10} more
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setViewModalOpen(false)}>
            Close
          </Button>
          <Button
            variant="primary"
            onClick={() => {
              setViewModalOpen(false);
              handleEdit(selectedUser!);
            }}
          >
            Edit User
          </Button>
        </ModalFooter>
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit User"
        size="md"
      >
        {selectedUser && (
          <div className="space-y-4">
            <Input
              label="Display Name"
              value={selectedUser.display_name}
              disabled
            />
            <Input
              label="Email"
              value={selectedUser.email}
              disabled
            />

            <div className="p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    Account Status
                  </h4>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {selectedUser.is_disabled
                      ? 'This user is currently disabled'
                      : 'This user is currently active'}
                  </p>
                </div>
                <Button
                  variant={selectedUser.is_disabled ? 'primary' : 'danger'}
                  size="sm"
                  onClick={handleToggleDisabled}
                  isLoading={updateUser.isPending}
                >
                  {selectedUser.is_disabled ? 'Enable' : 'Disable'}
                </Button>
              </div>
            </div>
          </div>
        )}
        <ModalFooter>
          <Button variant="secondary" onClick={() => setEditModalOpen(false)}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
};
