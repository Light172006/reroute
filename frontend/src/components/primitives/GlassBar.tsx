import React from 'react';

interface GlassBarProps extends React.HTMLAttributes<HTMLDivElement> {
  position?: 'top' | 'bottom' | 'static';
  border?: 'bottom' | 'top' | 'all' | 'none';
  children: React.ReactNode;
  className?: string;
}

export function GlassBar({
  position = 'static',
  border = 'bottom',
  children,
  className = '',
  ...props
}: GlassBarProps) {
  const positionClasses = {
    top: 'sticky top-0 z-40',
    bottom: 'sticky bottom-0 z-40',
    static: 'relative',
  };

  const borderClasses = {
    bottom: 'border-b',
    top: 'border-t',
    all: 'border',
    none: 'border-0',
  };

  return (
    <div
      className={`glass-surface ${positionClasses[position]} ${borderClasses[border]} transition-colors ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
