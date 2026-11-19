import React from 'react';
import { ItemCategory } from '@/types/contract';
import {
  Landmark,
  Utensils,
  Building2,
  Mountain,
  Moon,
  ShoppingBag,
  Compass,
  Bus,
  Sparkles,
  LucideIcon,
} from 'lucide-react';

interface CategoryBadgeProps {
  category: ItemCategory;
  showIcon?: boolean;
  className?: string;
}

export function CategoryBadge({
  category,
  showIcon = true,
  className = '',
}: CategoryBadgeProps) {
  const categoryConfig: Record<
    string,
    { label: string; icon: LucideIcon; style: string }
  > = {
    sightseeing: {
      label: 'Sightseeing',
      icon: Landmark,
      style: 'bg-[var(--cat-sightseeing-bg)] text-[var(--cat-sightseeing-fg)] border-blue-200/50 dark:border-blue-900/50',
    },
    food: {
      label: 'Food & Dining',
      icon: Utensils,
      style: 'bg-[var(--cat-food-bg)] text-[var(--cat-food-fg)] border-orange-200/50 dark:border-orange-900/50',
    },
    culture: {
      label: 'Culture & Heritage',
      icon: Building2,
      style: 'bg-[var(--cat-culture-bg)] text-[var(--cat-culture-fg)] border-purple-200/50 dark:border-purple-900/50',
    },
    nature: {
      label: 'Nature & Parks',
      icon: Mountain,
      style: 'bg-[var(--cat-nature-bg)] text-[var(--cat-nature-fg)] border-green-200/50 dark:border-green-900/50',
    },
    nightlife: {
      label: 'Nightlife',
      icon: Moon,
      style: 'bg-[var(--cat-nightlife-bg)] text-[var(--cat-nightlife-fg)] border-indigo-200/50 dark:border-indigo-900/50',
    },
    shopping: {
      label: 'Shopping & Bazaars',
      icon: ShoppingBag,
      style: 'bg-[var(--cat-shopping-bg)] text-[var(--cat-shopping-fg)] border-pink-200/50 dark:border-pink-900/50',
    },
    adventure: {
      label: 'Adventure',
      icon: Compass,
      style: 'bg-[var(--cat-adventure-bg)] text-[var(--cat-adventure-fg)] border-red-200/50 dark:border-red-900/50',
    },
    transport: {
      label: 'Transport',
      icon: Bus,
      style: 'bg-[var(--cat-transport-bg)] text-[var(--cat-transport-fg)] border-border',
    },
    stay: {
      label: 'Stay',
      icon: Building2,
      style: 'bg-surface-alt text-text-secondary border-border',
    },
    other: {
      label: 'Activity',
      icon: Sparkles,
      style: 'bg-surface-alt text-text-secondary border-border',
    },
  };

  const config = categoryConfig[category] || categoryConfig.other;
  const IconComponent = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-pill text-xs font-medium border ${config.style} ${className}`}
    >
      {showIcon && <IconComponent size={16} strokeWidth={1.75} className="shrink-0" />}
      <span className="capitalize">{config.label}</span>
    </span>
  );
}
