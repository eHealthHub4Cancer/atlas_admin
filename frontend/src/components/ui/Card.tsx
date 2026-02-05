import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hover = false,
  padding = 'md',
}) => {
  return (
    <div
      className={cn(
        'bg-white dark:bg-dark-card rounded-2xl',
        'border border-light-border dark:border-dark-border',
        'shadow-soft transition-all duration-200',
        hover && 'hover:shadow-lg hover:border-brand-200 dark:hover:border-brand-800 hover:-translate-y-0.5 cursor-pointer',
        paddingStyles[padding],
        className
      )}
    >
      {children}
    </div>
  );
};

export interface CardHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  description,
  action,
  className,
}) => {
  return (
    <div className={cn('flex items-start justify-between mb-4', className)}>
      <div>
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          {title}
        </h3>
        {description && (
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {description}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  change?: {
    value: number;
    trend: 'up' | 'down' | 'neutral';
  };
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  change,
  className,
}) => {
  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">
            {value}
          </p>
          {change && (
            <div className="mt-2 flex items-center gap-1">
              <span
                className={cn(
                  'text-xs font-medium',
                  change.trend === 'up' && 'text-emerald-600 dark:text-emerald-400',
                  change.trend === 'down' && 'text-red-600 dark:text-red-400',
                  change.trend === 'neutral' && 'text-slate-500'
                )}
              >
                {change.trend === 'up' ? '+' : change.trend === 'down' ? '-' : ''}
                {Math.abs(change.value)}%
              </span>
              <span className="text-xs text-slate-500">from last month</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-3 rounded-xl bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};
