import React from 'react';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/20/solid';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';
import { Select } from '../ui/Select';

export interface PaginationProps {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  pageSizeOptions?: number[];
  isLoading?: boolean;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  pageSize,
  totalCount,
  totalPages,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  isLoading = false,
  className,
}) => {
  const startItem = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalCount);

  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    const showPages = 5;

    if (totalPages <= showPages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);

      if (page > 3) {
        pages.push('ellipsis');
      }

      // Show pages around current
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);

      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }

      if (page < totalPages - 2) {
        pages.push('ellipsis');
      }

      // Always show last page
      if (!pages.includes(totalPages)) {
        pages.push(totalPages);
      }
    }

    return pages;
  };

  return (
    <div className={cn('flex flex-col sm:flex-row items-center justify-between gap-4 py-4', className)}>
      {/* Results info */}
      <div className="flex items-center gap-4">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Showing <span className="font-medium text-slate-900 dark:text-slate-100">{startItem}</span> to{' '}
          <span className="font-medium text-slate-900 dark:text-slate-100">{endItem}</span> of{' '}
          <span className="font-medium text-slate-900 dark:text-slate-100">{totalCount}</span> results
        </p>

        {/* Page size selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600 dark:text-slate-400">Show</span>
          <Select
            options={pageSizeOptions.map((size) => ({ value: String(size), label: String(size) }))}
            value={String(pageSize)}
            onChange={(value) => onPageSizeChange(Number(value))}
            className="w-20"
          />
        </div>
      </div>

      {/* Page navigation */}
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={!canGoPrevious || isLoading}
          aria-label="Previous page"
        >
          <ChevronLeftIcon className="h-4 w-4" />
          <span className="sr-only sm:not-sr-only">Previous</span>
        </Button>

        {/* Page numbers */}
        <div className="hidden sm:flex items-center gap-1">
          {getPageNumbers().map((pageNum, index) =>
            pageNum === 'ellipsis' ? (
              <span
                key={`ellipsis-${index}`}
                className="px-2 text-slate-400"
              >
                ...
              </span>
            ) : (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                disabled={isLoading}
                className={cn(
                  'min-w-[2rem] h-8 px-2 rounded-lg text-sm font-medium transition-colors',
                  pageNum === page
                    ? 'bg-brand-500 text-white'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-dark-elevated'
                )}
              >
                {pageNum}
              </button>
            )
          )}
        </div>

        {/* Mobile page indicator */}
        <span className="sm:hidden text-sm text-slate-600 dark:text-slate-400">
          Page {page} of {totalPages}
        </span>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={!canGoNext || isLoading}
          aria-label="Next page"
        >
          <span className="sr-only sm:not-sr-only">Next</span>
          <ChevronRightIcon className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};
