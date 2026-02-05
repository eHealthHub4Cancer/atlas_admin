import React, { useMemo } from 'react';
import { type ColumnDef } from '@tanstack/react-table';
import { ArrowPathIcon } from '@heroicons/react/24/outline';
import { Card, CardHeader, Badge, Button } from '../../components/ui';
import { DataTable, Pagination, FilterBar, type FilterConfig } from '../../components/data-table';
import { useTableState, useAdminRoles, useSyncRoles } from '../../hooks';
import type { Permission } from '../../types';

const filterOptions = [
  { value: 'with_id', label: 'With External ID' },
  { value: 'no_id', label: 'Without External ID' },
];

const filters: FilterConfig[] = [
  {
    key: 'filter',
    label: 'External ID',
    type: 'select',
    options: filterOptions,
    placeholder: 'All roles',
  },
];

export const RolesPage: React.FC = () => {
  const tableState = useTableState({
    defaultPageSize: 10,
    syncWithUrl: true,
    filterKeys: ['filter'],
  });

  const { data, isLoading, isError, refetch } = useAdminRoles({
    page: tableState.page,
    page_size: tableState.pageSize,
    search: tableState.search,
    filter: tableState.filters.filter,
    ordering: tableState.sorting.length > 0
      ? (tableState.sorting[0].desc ? '-' : '') + tableState.sorting[0].id
      : undefined,
  });

  const syncRoles = useSyncRoles();

  const columns: ColumnDef<Permission>[] = useMemo(
    () => [
      {
        id: 'name',
        header: 'Role Name',
        accessorKey: 'name',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {row.original.name}
          </span>
        ),
      },
      {
        id: 'external_id',
        header: 'External ID',
        accessorKey: 'external_id',
        enableSorting: true,
        cell: ({ row }) => (
          row.original.external_id ? (
            <Badge variant="primary">{row.original.external_id}</Badge>
          ) : (
            <span className="text-slate-400">—</span>
          )
        ),
      },
      {
        id: 'description',
        header: 'Description',
        accessorKey: 'description',
        cell: ({ row }) => (
          <span className="text-slate-600 dark:text-slate-400">
            {row.original.description || '—'}
          </span>
        ),
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Roles Management
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            View and sync roles from WebAPI
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => syncRoles.mutate()}
          isLoading={syncRoles.isPending}
          leftIcon={<ArrowPathIcon className="h-4 w-4" />}
        >
          Sync from WebAPI
        </Button>
      </div>

      <Card>
        <CardHeader
          title="All Roles"
          description="Roles synced from the WebAPI security system"
        />

        <FilterBar
          searchValue={tableState.search}
          onSearchChange={tableState.setSearch}
          filters={filters}
          filterValues={tableState.filters}
          onFilterChange={tableState.setFilter}
          onClearFilters={tableState.clearFilters}
          placeholder="Search roles..."
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
          emptyMessage="No roles found"
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

      {/* Info card */}
      <Card className="bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800">
        <div className="flex gap-4">
          <ArrowPathIcon className="h-6 w-6 text-brand-600 dark:text-brand-400 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-medium text-brand-900 dark:text-brand-100">
              About Role Synchronization
            </h3>
            <p className="mt-1 text-sm text-brand-700 dark:text-brand-300">
              Roles are synced from the WebAPI security system. Click "Sync from WebAPI" to
              fetch the latest roles. Roles with an External ID are linked to the WebAPI
              sec_role table.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
