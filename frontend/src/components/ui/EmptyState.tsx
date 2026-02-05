import React from 'react';
import { FolderOpenIcon, MagnifyingGlassIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  variant?: 'default' | 'search' | 'error';
  className?: string;
}

const defaultIcons = {
  default: FolderOpenIcon,
  search: MagnifyingGlassIcon,
  error: ExclamationCircleIcon,
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  variant = 'default',
  className,
}) => {
  const DefaultIcon = defaultIcons[variant];

  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-4 text-center', className)}>
      <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-dark-elevated flex items-center justify-center mb-4">
        {icon || <DefaultIcon className="w-8 h-8 text-slate-400" />}
      </div>
      <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm">
          {description}
        </p>
      )}
      {action && (
        <Button
          variant="primary"
          onClick={action.onClick}
          className="mt-4"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
};

// Error state variant
export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({
  title = 'Something went wrong',
  message = 'An error occurred while loading the data. Please try again.',
  onRetry,
}) => {
  return (
    <EmptyState
      variant="error"
      title={title}
      description={message}
      action={onRetry ? { label: 'Try Again', onClick: onRetry } : undefined}
    />
  );
};

// No results state variant
export const NoResultsState: React.FC<{
  searchQuery?: string;
  onClear?: () => void;
}> = ({ searchQuery, onClear }) => {
  return (
    <EmptyState
      variant="search"
      title="No results found"
      description={
        searchQuery
          ? `No results match "${searchQuery}". Try adjusting your search or filters.`
          : 'Try adjusting your search or filters.'
      }
      action={onClear ? { label: 'Clear filters', onClick: onClear } : undefined}
    />
  );
};
