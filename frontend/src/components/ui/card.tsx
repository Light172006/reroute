import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover = false, ...props }: CardProps) {
  return (
    <div
      className={twMerge(
        clsx(
          'card-surface overflow-hidden',
          hover && 'card-surface-hover cursor-pointer',
          className
        )
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={twMerge(clsx('flex flex-col space-y-1.5 p-4 sm:p-5', className))}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={twMerge(
        clsx('text-h3 font-semibold text-text-primary tracking-tight', className)
      )}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={twMerge(clsx('text-small text-text-secondary', className))}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge(clsx('p-4 sm:p-5 pt-0', className))} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={twMerge(clsx('flex items-center p-4 sm:p-5 pt-0', className))}
      {...props}
    />
  );
}
