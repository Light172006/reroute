'use client';

import React from 'react';
import { ItineraryItem, ItemCategory } from '@/types/contract';
import { formatCurrency, formatTime } from '@/lib/format';
import { IconCircle } from '@/components/primitives/IconCircle';
import { Button } from '@/components/ui/button';
import {
  Lock,
  Unlock,
  GripVertical,
  Trash2,
  Edit2,
  Clock,
  Landmark,
  Utensils,
  Building2,
  Mountain,
  Moon,
  ShoppingBag,
  Compass,
  Bus,
  Sun,
  CloudRain,
  MapPin,
  Sparkles,
} from 'lucide-react';

interface ItineraryItemCardProps {
  item: ItineraryItem;
  currency?: string;
  isHighlighted?: boolean;
  isAffectedByProposal?: boolean;
  onToggleLock: (isLocked: boolean) => void;
  onDelete: () => void;
  onEdit?: (item: ItineraryItem) => void;
  dragHandleProps?: Record<string, unknown>;
}

const getCategoryIconComponent = (category: ItemCategory) => {
  switch (category) {
    case 'food':
      return Utensils;
    case 'sightseeing':
      return Landmark;
    case 'culture':
      return Building2;
    case 'nature':
      return Mountain;
    case 'nightlife':
      return Moon;
    case 'shopping':
      return ShoppingBag;
    case 'adventure':
      return Compass;
    case 'transport':
      return Bus;
    default:
      return Sparkles;
  }
};

export function ItineraryItemCard({
  item,
  currency = 'INR',
  isHighlighted = false,
  isAffectedByProposal = false,
  onToggleLock,
  onDelete,
  onEdit,
  dragHandleProps,
}: ItineraryItemCardProps) {
  const IconComponent = getCategoryIconComponent(item.category);

  // Approximate duration in minutes
  const durationMin = React.useMemo(() => {
    if (!item.start_time || !item.end_time) return null;
    const [h1, m1] = item.start_time.split(':').map(Number);
    const [h2, m2] = item.end_time.split(':').map(Number);
    return (h2 - h1) * 60 + (m2 - m1);
  }, [item.start_time, item.end_time]);

  return (
    <div
      id={`item-card-${item.id}`}
      className={`card-surface group relative flex items-start p-4 sm:p-5 transition-all ${
        item.is_locked ? 'border-l-[3px] border-l-primary' : ''
      } ${
        isHighlighted
          ? 'ring-2 ring-primary border-primary shadow-md'
          : isAffectedByProposal
          ? 'border-accent-border bg-accent-bg/40'
          : 'hover:border-border-muted'
      }`}
    >
      {/* Left Time Column (Fixed 64px width in tabular mono) */}
      <div className="w-16 shrink-0 pt-0.5 text-left tabular-mono">
        <div className="text-small font-bold text-text-primary">
          {formatTime(item.start_time)}
        </div>
        <div className="text-caption text-text-muted mt-0.5">
          {formatTime(item.end_time)}
        </div>
      </div>

      {/* Category Icon Circle */}
      <div className="mr-3 shrink-0">
        <IconCircle icon={IconComponent} variant={item.category} size="md" />
      </div>

      {/* Center Content Column */}
      <div className="flex-1 min-w-0 pr-3 space-y-1.5">
        <div className="flex items-center gap-2">
          <h3 className="text-h3 font-semibold text-text-primary truncate">
            {item.title}
          </h3>
          {item.is_locked && (
            <span
              title="Locked: will never be changed by AI replanning"
              className="text-primary inline-flex items-center shrink-0"
              role="img"
              aria-label="Item is locked"
            >
              <Lock size={16} strokeWidth={1.75} aria-hidden="true" />
            </span>
          )}
        </div>

        {/* Metadata row with icons (clock, map-pin) */}
        <div className="flex flex-wrap items-center gap-3 text-caption text-text-secondary">
          {durationMin !== null && durationMin > 0 && (
            <span className="flex items-center gap-1 tabular-mono">
              <Clock size={16} strokeWidth={1.75} className="text-text-muted shrink-0" aria-hidden="true" />
              <span>{durationMin} min</span>
            </span>
          )}
          {item.setting && (
            <span className="flex items-center gap-1 capitalize">
              <MapPin size={16} strokeWidth={1.75} className="text-text-muted shrink-0" aria-hidden="true" />
              <span>{item.setting}</span>
            </span>
          )}
        </div>

        {item.notes && (
          <p className="text-small text-text-secondary line-clamp-2 pt-0.5">
            {item.notes}
          </p>
        )}

        {/* Pill Badges with SVG Icons (Sun for outdoor, cloud-rain for risk, clock for closes soon, lock for locked) */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          {item.setting === 'outdoor' && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-pill text-caption font-medium bg-surface-alt text-text-secondary border border-border">
              <Sun size={16} strokeWidth={1.75} className="text-amber-500" aria-hidden="true" />
              <span>Outdoor</span>
            </span>
          )}

          {item.flags?.includes('weather_risk') && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-pill text-caption font-semibold bg-accent-bg text-accent-text border border-accent-border">
              <CloudRain size={16} strokeWidth={1.75} className="text-accent" aria-hidden="true" />
              <span>Weather risk</span>
            </span>
          )}

          {item.flags?.includes('closes_5pm') && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-pill text-caption font-medium bg-surface-alt text-text-secondary border border-border">
              <Clock size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
              <span>Closes 5pm</span>
            </span>
          )}

          {item.is_locked && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-pill text-caption font-medium bg-primary/10 text-primary border border-primary/20">
              <Lock size={16} strokeWidth={1.75} aria-hidden="true" />
              <span>Locked</span>
            </span>
          )}
        </div>
      </div>

      {/* Right Column: Amount in tabular mono + Action buttons */}
      <div className="flex flex-col items-end justify-between self-stretch shrink-0">
        <span className="tabular-mono text-small font-bold text-text-primary text-right">
          {formatCurrency(item.est_cost, currency)}
        </span>

        <div className="flex items-center gap-1 pt-3">
          {/* Lock / Unlock */}
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => onToggleLock(!item.is_locked)}
            aria-label={item.is_locked ? 'Unlock item' : 'Lock item'}
            className={
              item.is_locked
                ? 'text-primary bg-primary/10'
                : 'text-text-muted hover:text-text-primary'
            }
          >
            {item.is_locked ? (
              <Lock size={16} strokeWidth={1.75} />
            ) : (
              <Unlock size={16} strokeWidth={1.75} />
            )}
          </Button>

          {/* Edit */}
          {onEdit && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => onEdit(item)}
              aria-label="Edit stop details"
              className="text-text-muted hover:text-text-primary"
            >
              <Edit2 size={16} strokeWidth={1.75} />
            </Button>
          )}

          {/* Remove */}
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onDelete}
            aria-label="Remove stop from itinerary"
            className="text-text-muted hover:text-danger hover:bg-danger-bg"
          >
            <Trash2 size={16} strokeWidth={1.75} />
          </Button>

          {/* Drag Handle: visible on hover on desktop, always on touch */}
          <div
            {...dragHandleProps}
            className={`p-1.5 rounded-input text-text-muted hover:text-text-primary cursor-grab active:cursor-grabbing opacity-70 group-hover:opacity-100 transition-opacity ${
              item.is_locked ? 'opacity-20 cursor-not-allowed pointer-events-none' : ''
            }`}
            aria-label={item.is_locked ? 'Locked item cannot be dragged' : 'Drag to reorder stop'}
          >
            <GripVertical size={20} strokeWidth={1.75} />
          </div>
        </div>
      </div>
    </div>
  );
}
