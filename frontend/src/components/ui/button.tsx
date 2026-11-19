import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'accent';
  size?: 'sm' | 'md' | 'lg' | 'default' | 'icon' | 'icon-sm';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const resolvedSize = size === 'default' ? 'md' : size;
    const base =
      'inline-flex items-center justify-center font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none rounded-[8px] select-none text-small';

    const variants = {
      primary:
        'btn-primary-gradient shadow-sm active:scale-[0.98]',
      secondary:
        'bg-surface-alt text-text-primary hover:bg-border active:scale-[0.98]',
      outline:
        'border border-border bg-transparent hover:bg-surface-alt text-text-primary active:scale-[0.98]',
      ghost:
        'bg-transparent hover:bg-surface-alt text-text-secondary hover:text-text-primary active:scale-[0.98]',
      danger:
        'bg-danger text-white hover:bg-red-700 active:bg-red-800 shadow-xs active:scale-[0.98]',
      accent:
        'bg-accent text-black hover:bg-amber-600 active:bg-amber-700 font-semibold shadow-xs active:scale-[0.98]',
    };

    const sizes = {
      sm: 'h-[36px] px-3 gap-1.5',
      md: 'h-[40px] px-4 gap-2',
      lg: 'h-[48px] px-6 text-base gap-2.5',
      icon: 'h-[40px] w-[40px] p-0',
      'icon-sm': 'h-[36px] w-[36px] p-0',
    };

    return (
      <button
        ref={ref}
        className={twMerge(clsx(base, variants[variant], sizes[resolvedSize], className))}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
