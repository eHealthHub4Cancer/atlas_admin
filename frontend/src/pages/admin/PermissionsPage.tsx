import React, { useMemo } from 'react';
import { type ColumnDef } from '@tanstack/react-table';
import { Card, CardHeader, Badge } from '../../components/ui';
import { DataTable, Pagination, FilterBar, type FilterConfig } from '../../components/data-table';
import { useTableState, useAdminPermissions } from '../../hooks';
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
    placeholder: 'All permissions',
  },
];

export const PermissionsPage: React.FC = () => {
  const tableState = useTableState({
    defaultPageSize: 10,
    syncWithUrl: true,
    filterKeys: ['filter'],
  });

  const { data, isLoading, isError, refetch } = useAdminPermissions({
    page: tableState.page,
    page_size: tableState.pageSize,
    search: tableState.search,
    filter: tableState.filters.filter,
    ordering: tableState.sorting.length > 0
      ? (tableState.sorting[0].desc ? '-' : '') + tableState.sorting[0].id
      : undefined,
  });

  const columns: ColumnDef<Permission>[] = useMemo(
    () => [
      {
        id: 'name',
        header: 'Permission Name',
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
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Permissions
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          View all available permissions
        </p>
      </div>

      <Card>
        <CardHeader
          title="All Permissions"
          description="Permissions available for assignment to users"
        />

        <FilterBar
          searchValue={tableState.search}
          onSearchChange={tableState.setSearch}
          filters={filters}
          filterValues={tableState.filters}
          onFilterChange={tableState.setFilter}
          onClearFilters={tableState.clearFilters}
          placeholder="Search permissions..."
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
          emptyMessage="No permissions found"
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
    </div>
  );
};
