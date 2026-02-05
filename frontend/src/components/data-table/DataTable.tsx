import React from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table';
import { ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/20/solid';
import { cn } from '../../lib/utils';
import { TableRowSkeleton } from '../ui/Skeleton';
import { EmptyState, ErrorState, NoResultsState } from '../ui/EmptyState';

export interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  isLoading?: boolean;
  isError?: boolean;
  error?: string;
  sorting?: SortingState;
  onSortingChange?: (sorting: SortingState) => void;
  emptyMessage?: string;
  searchQuery?: string;
  onClearSearch?: () => void;
  onRetry?: () => void;
  className?: string;
  stickyHeader?: boolean;
}

export function DataTable<T>({
  data,
  columns,
  isLoading = false,
  isError = false,
  error,
  sorting = [],
  onSortingChange,
  emptyMessage = 'No data available',
  searchQuery,
  onClearSearch,
  onRetry,
  className,
  stickyHeader = false,
}: DataTableProps<T>) {
  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
    },
    onSortingChange: (updater) => {
      if (onSortingChange) {
        const newSorting = typeof updater === 'function' ? updater(sorting) : updater;
        onSortingChange(newSorting);
      }
    },
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
  });

  // Error state
  if (isError && !isLoading) {
    return (
      <div className={cn('rounded-xl border border-light-border dark:border-dark-border overflow-hidden', className)}>
        <ErrorState
          title="Failed to load data"
          message={error || 'An error occurred while loading the data.'}
          onRetry={onRetry}
        />
      </div>
    );
  }

  return (
    <div className={cn('rounded-xl border border-light-border dark:border-dark-border overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-light-border dark:divide-dark-border">
          <thead className={cn(
            'bg-slate-50 dark:bg-dark-elevated',
            stickyHeader && 'sticky top-0 z-10'
          )}>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sortDirection = header.column.getIsSorted();

                  return (
                    <th
                      key={header.id}
                      scope="col"
                      className={cn(
                        'px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider',
                        canSort && 'cursor-pointer select-none hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors'
                      )}
                      onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                    >
                      <div className="flex items-center gap-2">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && (
                          <span className="flex flex-col">
                            <ChevronUpIcon
                              className={cn(
                                'h-3 w-3 -mb-1',
                                sortDirection === 'asc' ? 'text-brand-500' : 'text-slate-300 dark:text-slate-600'
                              )}
                            />
                            <ChevronDownIcon
                              className={cn(
                                'h-3 w-3',
                                sortDirection === 'desc' ? 'text-brand-500' : 'text-slate-300 dark:text-slate-600'
                              )}
                            />
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-light-border dark:divide-dark-border">
            {isLoading ? (
              // Loading skeleton
              Array.from({ length: 5 }).map((_, index) => (
                <TableRowSkeleton key={index} columns={columns.length} />
              ))
            ) : data.length === 0 ? (
              // Empty state
              <tr>
                <td colSpan={columns.length}>
                  {searchQuery ? (
                    <NoResultsState searchQuery={searchQuery} onClear={onClearSearch} />
                  ) : (
                    <EmptyState title={emptyMessage} />
                  )}
                </td>
              </tr>
            ) : (
              // Data rows
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="bg-white dark:bg-dark-card hover:bg-slate-50 dark:hover:bg-dark-elevated transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300 whitespace-nowrap"
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
