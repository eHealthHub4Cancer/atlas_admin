import React, { useMemo } from 'react';
import { type ColumnDef } from '@tanstack/react-table';
import { Card, CardHeader, Badge } from '../../components/ui';
import { DataTable, Pagination, FilterBar, type FilterConfig } from '../../components/data-table';
import { useTableState, useUserActivity } from '../../hooks';
import { formatDateTime } from '../../lib/utils';
import type { ActivityLog } from '../../types';

const statusOptions = [
  { value: 'success', label: 'Success' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'info', label: 'Info' },
];

const filters: FilterConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: statusOptions,
    placeholder: 'All statuses',
  },
  {
    key: 'date',
    label: 'Date',
    type: 'dateRange',
  },
];

export const ActivityPage: React.FC = () => {
  const tableState = useTableState({
    defaultPageSize: 10,
    syncWithUrl: true,
    filterKeys: ['status', 'date_from', 'date_to'],
  });

  const { data, isLoading, isError, refetch } = useUserActivity({
    page: tableState.page,
    page_size: tableState.pageSize,
    search: tableState.search,
    status: tableState.filters.status,
    date_from: tableState.filters.date_from,
    date_to: tableState.filters.date_to,
    ordering: tableState.sorting.length > 0
      ? (tableState.sorting[0].desc ? '-' : '') + tableState.sorting[0].id
      : undefined,
  });

  const columns: ColumnDef<ActivityLog>[] = useMemo(
    () => [
      {
        id: 'timestamp',
        header: 'Date & Time',
        accessorKey: 'timestamp',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="text-slate-900 dark:text-slate-100">
            {formatDateTime(row.original.timestamp)}
          </span>
        ),
      },
      {
        id: 'action',
        header: 'Action',
        accessorKey: 'action',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {row.original.action}
          </span>
        ),
      },
      {
        id: 'summary',
        header: 'Summary',
        accessorKey: 'summary',
        cell: ({ row }) => (
          <span className="text-slate-600 dark:text-slate-400">
            {row.original.summary}
          </span>
        ),
      },
      {
        id: 'status',
        header: 'Status',
        accessorKey: 'status',
        enableSorting: true,
        cell: ({ row }) => {
          const status = row.original.status;
          const variant = {
            success: 'success',
            warning: 'warning',
            error: 'danger',
            info: 'primary',
          }[status] as 'success' | 'warning' | 'danger' | 'primary';

          return (
            <Badge variant={variant} dot>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
          );
        },
      },
    ],
    []
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Activity Log
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          View your account activity history
        </p>
      </div>

      <Card>
        <CardHeader
          title="Recent Activity"
          description="A log of actions performed on your account"
        />

        <FilterBar
          searchValue={tableState.search}
          onSearchChange={tableState.setSearch}
          filters={filters}
          filterValues={tableState.filters}
          onFilterChange={tableState.setFilter}
          onClearFilters={tableState.clearFilters}
          placeholder="Search activities..."
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
          emptyMessage="No activity recorded yet"
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
