import React from 'react';
import { Transition } from '@headlessui/react';
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useToastStore, type ToastType } from '../../store/toast';
import { cn } from '../../lib/utils';

const toastIcons: Record<ToastType, React.ElementType> = {
  success: CheckCircleIcon,
  error: XCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon,
};

const toastStyles: Record<ToastType, string> = {
  success: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
  error: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
  warning: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
  info: 'bg-brand-50 dark:bg-brand-900/20 border-brand-200 dark:border-brand-800',
};

const iconStyles: Record<ToastType, string> = {
  success: 'text-emerald-500',
  error: 'text-red-500',
  warning: 'text-amber-500',
  info: 'text-brand-500',
};

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useToastStore();

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => {
        const Icon = toastIcons[toast.type];

        return (
          <Transition
            key={toast.id}
            appear
            show={true}
            enter="transform transition duration-300 ease-out"
            enterFrom="translate-x-full opacity-0"
            enterTo="translate-x-0 opacity-100"
            leave="transform transition duration-200 ease-in"
            leaveFrom="translate-x-0 opacity-100"
            leaveTo="translate-x-full opacity-0"
          >
            <div
              className={cn(
                'pointer-events-auto rounded-xl border p-4 shadow-lg',
                'bg-white dark:bg-dark-card',
                toastStyles[toast.type]
              )}
              role="alert"
            >
              <div className="flex items-start gap-3">
                <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', iconStyles[toast.type])} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {toast.title}
                  </p>
                  {toast.message && (
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {toast.message}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => removeToast(toast.id)}
                  className={cn(
                    'flex-shrink-0 rounded-lg p-1',
                    'text-slate-400 hover:text-slate-500 dark:hover:text-slate-300',
                    'hover:bg-slate-100 dark:hover:bg-dark-elevated',
                    'transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500'
                  )}
                >
                  <span className="sr-only">Dismiss</span>
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </Transition>
        );
      })}
    </div>
  );
};
