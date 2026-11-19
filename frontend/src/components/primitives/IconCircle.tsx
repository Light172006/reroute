import React from 'react';
import { LucideIcon } from 'lucide-react';
import { ItemCategory } from '@/types/contract';

export type IconCircleVariant =
  | 'primary'
  | 'accent'
  | 'success'
  | 'danger'
  | 'neutral'
  | 'blue'
  | 'orange'
  | 'violet'
  | 'green'
  | 'indigo'
  | 'pink'
  | 'red'
  | 'slate'
  | ItemCategory;

export interface IconCircleProps {
  icon?: LucideIcon;
  variant?: IconCircleVariant;
  color?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  'aria-hidden'?: boolean;
  children?: React.ReactNode;
}

export function IconCircle({
  icon: Icon,
  variant,
  color,
  size = 'md',
  className = '',
  'aria-hidden': ariaHidden = true,
  children,
}: IconCircleProps) {
  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
  };

  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 24,
  };

  const key = (color || variant || 'primary') as string;

  const variantStyles: Record<string, string> = {
    primary: 'bg-primary-50 text-primary dark:bg-primary-50 dark:text-primary',
    blue: 'bg-primary-50 text-primary dark:bg-primary-50 dark:text-primary',
    accent: 'bg-accent-bg text-accent-text border border-accent-border',
    orange: 'bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200/80 dark:border-amber-900/60',
    success: 'bg-success-bg text-success-text border border-success-border',
    green: 'bg-green-50 text-success dark:bg-green-950/60 dark:text-green-400 border border-green-200/80 dark:border-green-900/60',
    danger: 'bg-danger-bg text-danger-text border border-danger-border',
    red: 'bg-red-50 text-danger dark:bg-red-950/60 dark:text-red-400 border border-red-200/80 dark:border-red-900/60',
    violet: 'bg-purple-50 text-purple-600 dark:bg-purple-950/60 dark:text-purple-400 border border-purple-200/80 dark:border-purple-900/60',
    indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 border border-indigo-200/80 dark:border-indigo-900/60',
    pink: 'bg-pink-50 text-pink-600 dark:bg-pink-950/60 dark:text-pink-400 border border-pink-200/80 dark:border-pink-900/60',
    slate: 'bg-surface-alt text-text-secondary',
    neutral: 'bg-surface-alt text-text-secondary',
    sightseeing: 'bg-[var(--cat-sightseeing-bg)] text-[var(--cat-sightseeing-fg)]',
    food: 'bg-[var(--cat-food-bg)] text-[var(--cat-food-fg)]',
    culture: 'bg-[var(--cat-culture-bg)] text-[var(--cat-culture-fg)]',
    nature: 'bg-[var(--cat-nature-bg)] text-[var(--cat-nature-fg)]',
    nightlife: 'bg-[var(--cat-nightlife-bg)] text-[var(--cat-nightlife-fg)]',
    shopping: 'bg-[var(--cat-shopping-bg)] text-[var(--cat-shopping-fg)]',
    adventure: 'bg-[var(--cat-adventure-bg)] text-[var(--cat-adventure-fg)]',
    transport: 'bg-[var(--cat-transport-bg)] text-[var(--cat-transport-fg)]',
    stay: 'bg-surface-alt text-text-secondary',
    other: 'bg-surface-alt text-text-secondary',
  };

  const styleClass = variantStyles[key] || variantStyles.primary;

  return (
    <div
      className={`rounded-full flex items-center justify-center shrink-0 transition-colors ${sizeClasses[size]} ${styleClass} ${className}`}
      aria-hidden={ariaHidden}
    >
      {Icon ? <Icon size={iconSizes[size]} strokeWidth={1.75} className="currentColor" /> : children}
    </div>
  );
}
