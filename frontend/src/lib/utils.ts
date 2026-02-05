import { clsx, type ClassValue } from 'clsx';
import { format, formatDistanceToNow } from 'date-fns';

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

export const debounce = <T extends (...args: Parameters<T>) => void>(fn: T, wait = 300) => {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
    }, wait);
  };
};

export const formatDateTime = (value?: string | number | Date) => {
  if (!value) return '';
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value;
  return format(date, 'PPp');
};

export const formatRelativeTime = (value?: string | number | Date) => {
  if (!value) return '';
  const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : value;
  return formatDistanceToNow(date, { addSuffix: true });
};

export const capitalize = (value?: string) => {
  if (!value) return '';
  return value.charAt(0).toUpperCase() + value.slice(1);
};

export const getInitials = (value?: string) => {
  if (!value) return '';
  const parts = value.trim().split(/\s+/);
  const initials = parts.slice(0, 2).map((part) => part.charAt(0).toUpperCase());
  return initials.join('');
};
