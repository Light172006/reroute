import React from 'react';
import { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  level?: 'h1' | 'h2' | 'h3';
  className?: string;
}

export function SectionHeader({
  title,
  description,
  icon: Icon,
  action,
  level = 'h2',
  className = '',
}: SectionHeaderProps) {
  const TitleTag = level;
  const titleClass =
    level === 'h1' ? 'text-h1' : level === 'h2' ? 'text-h2' : 'text-h3';

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 ${className}`}
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <div className="p-1.5 rounded-input bg-primary/10 text-primary shrink-0">
              <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
            </div>
          )}
          <TitleTag className={`${titleClass} font-bold text-text-primary tracking-tight`}>
            {title}
          </TitleTag>
        </div>
        {description && (
          <p className="text-small text-text-secondary">
            {description}
          </p>
        )}
      </div>

      {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
    </div>
  );
}
