import React from 'react';
import { ExclamationTriangleIcon, TrashIcon, ShieldExclamationIcon } from '@heroicons/react/24/outline';
import { Modal, ModalFooter } from './Modal';
import { Button } from './Button';
import { cn } from '../../lib/utils';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  isLoading?: boolean;
}

const iconStyles = {
  danger: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    icon: TrashIcon,
    iconColor: 'text-red-600 dark:text-red-400',
  },
  warning: {
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    icon: ExclamationTriangleIcon,
    iconColor: 'text-amber-600 dark:text-amber-400',
  },
  info: {
    bg: 'bg-brand-100 dark:bg-brand-900/30',
    icon: ShieldExclamationIcon,
    iconColor: 'text-brand-600 dark:text-brand-400',
  },
};

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
  isLoading = false,
}) => {
  const styles = iconStyles[variant];
  const Icon = styles.icon;

  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="sm" showClose={false}>
      <div className="flex gap-4">
        <div className={cn('flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center', styles.bg)}>
          <Icon className={cn('w-5 h-5', styles.iconColor)} />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h3>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {message}
          </p>
        </div>
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={isLoading}>
          {cancelText}
        </Button>
        <Button
          variant={variant === 'danger' ? 'danger' : 'primary'}
          onClick={handleConfirm}
          isLoading={isLoading}
        >
          {confirmText}
        </Button>
      </ModalFooter>
    </Modal>
  );
};
