import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}

const variantStyles = {
  primary: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300',
  success: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300',
  warning: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  danger: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  neutral: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400',
};

const dotColors = {
  primary: 'bg-brand-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  neutral: 'bg-slate-500',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-xs',
};

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  size = 'md',
  children,
  className,
  dot = false,
}) => {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-full',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot && (
        <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant])} />
      )}
      {children}
    </span>
  );
};
