import React from 'react';
import { cn } from '../../lib/utils';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
}

const variantStyles = {
  text: 'rounded',
  circular: 'rounded-full',
  rectangular: 'rounded-none',
  rounded: 'rounded-xl',
};

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'text',
  width,
  height,
  animation = 'wave',
}) => {
  return (
    <div
      className={cn(
        'bg-slate-200 dark:bg-slate-700',
        animation === 'pulse' && 'animate-pulse',
        animation === 'wave' && 'skeleton',
        variantStyles[variant],
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
};

// Table row skeleton
export const TableRowSkeleton: React.FC<{ columns: number }> = ({ columns }) => {
  return (
    <tr className="bg-white dark:bg-dark-card">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton height={20} className="w-full" />
        </td>
      ))}
    </tr>
  );
};

// Card skeleton
export const CardSkeleton: React.FC<{ lines?: number }> = ({ lines = 3 }) => {
  return (
    <div className="card p-6 space-y-4">
      <Skeleton height={24} width="40%" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={16} width={`${80 - i * 10}%`} />
      ))}
    </div>
  );
};

// Stat card skeleton
export const StatCardSkeleton: React.FC = () => {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <Skeleton height={16} width="60%" />
          <Skeleton height={36} width="40%" />
          <Skeleton height={12} width="80%" />
        </div>
        <Skeleton variant="rounded" width={48} height={48} />
      </div>
    </div>
  );
};
