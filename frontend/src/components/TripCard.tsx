import React from 'react';
import Link from 'next/link';
import { Trip } from '@/types/contract';
import { formatDateRange, formatCurrency } from '@/lib/format';
import { StatusChip } from '@/components/primitives/StatusChip';
import { Calendar, Users, MapPin } from 'lucide-react';

interface TripCardProps {
  trip: Trip;
}

export function TripCard({ trip }: TripCardProps) {
  const hasImage = !!trip.image_url;

  return (
    <Link href={`/trips/${trip.id}`} className="block group focus:outline-none">
      <div className="card-surface card-surface-hover overflow-hidden flex flex-col h-full group-focus-visible:ring-2 group-focus-visible:ring-primary">
        {/* Full-bleed destination image with bottom gradient overlay */}
        <div className="relative h-48 w-full bg-surface-alt overflow-hidden">
          {hasImage ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={trip.image_url}
              alt={trip.destination}
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="h-full w-full bg-gradient-to-br from-primary to-[var(--primary-gradient-to)] dark:from-surface-raised dark:to-surface-alt flex items-center justify-center text-white/40 dark:text-text-muted">
              <MapPin size={48} strokeWidth={1.5} />
            </div>
          )}

          {/* Top Status Chip */}
          <div className="absolute top-3 right-3 z-10">
            <StatusChip
              status={trip.status}
              hasPendingProposal={trip.has_pending_proposal}
            />
          </div>

          {/* Gradient Overlay carrying Destination Title and Dates */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent flex flex-col justify-end p-4 text-white">
            <h3 className="text-h3 font-bold text-white group-hover:text-primary transition-colors truncate drop-shadow-xs">
              {trip.title}
            </h3>
            <div className="flex items-center gap-2 text-xs text-white/90 mt-1 font-medium">
              <MapPin size={16} strokeWidth={1.75} className="text-white/70 shrink-0" aria-hidden="true" />
              <span className="truncate">{trip.destination}</span>
              <span>•</span>
              <Calendar size={16} strokeWidth={1.75} className="text-white/70 shrink-0" aria-hidden="true" />
              <span>{formatDateRange(trip.start_date, trip.end_date)}</span>
            </div>
          </div>
        </div>

        {/* Card Body & Metadata */}
        <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-3 bg-surface">
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span className="flex items-center gap-1.5">
              <Users size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
              <span>{trip.group_size} {trip.group_size === 1 ? 'traveler' : 'travelers'}</span>
            </span>
            <span className="capitalize px-2 py-0.5 rounded-pill bg-surface-alt text-[11px] font-medium text-text-secondary">
              {trip.pace} pace
            </span>
          </div>

          <div className="pt-3 border-t border-border flex items-baseline justify-between">
            <span className="text-caption uppercase tracking-wider text-text-muted font-medium">
              Budget
            </span>
            <span className="tabular-mono text-small font-bold text-text-primary">
              {formatCurrency(trip.budget_total, trip.currency)}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
