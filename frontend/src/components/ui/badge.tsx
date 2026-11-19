import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'accent' | 'danger' | 'success' | 'outline';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const base = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium gap-1';
  const variants = {
    default: 'bg-primary/10 text-primary border border-primary/20',
    secondary: 'bg-surface-alt text-text-secondary border border-border',
    accent: 'bg-accent-bg text-accent-text border border-accent-border',
    danger: 'bg-danger-bg text-danger-text border border-danger-border',
    success: 'bg-success-bg text-success-text border border-success-border',
    outline: 'border border-border text-text-primary',
  };

  return <span className={twMerge(clsx(base, variants[variant], className))} {...props} />;
}
