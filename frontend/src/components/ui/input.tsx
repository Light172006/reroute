import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={twMerge(
          clsx(
            'flex h-[40px] w-full rounded-input border border-border bg-surface-alt px-3.5 py-2 text-small ring-offset-background file:border-0 file:bg-transparent file:text-small file:font-medium placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 text-text-primary transition-colors',
            className
          )
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';
