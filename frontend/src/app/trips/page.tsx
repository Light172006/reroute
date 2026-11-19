'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTrips } from '@/hooks/useTrip';
import { api } from '@/lib/api';
import { TripCard } from '@/components/TripCard';
import { Button } from '@/components/ui/button';
import { Plus, Compass, Sparkles, AlertCircle } from 'lucide-react';
import { IconCircle } from '@/components/primitives/IconCircle';

export default function TripsPage() {
  const router = useRouter();
  const { data: trips = [], isLoading, error } = useTrips();

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push('/login');
    }
  }, [router]);

  return (
    <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8 w-full flex-1">
      {/* Subtle decorative background blur mesh */}
      <div
        className="pointer-events-none absolute -top-12 right-1/4 -z-10 h-64 w-64 rounded-full bg-primary/10 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute top-48 left-1/3 -z-10 h-72 w-72 rounded-full bg-[var(--primary-gradient-to)]/10 blur-3xl"
        aria-hidden="true"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary">
            My Trips
          </h1>
          <p className="text-sm text-text-secondary">
            Active and upcoming journeys monitored in real time by Reroute
          </p>
        </div>

        <Link href="/trips/new">
          <Button variant="primary" className="gap-2 shadow-sm font-semibold">
            <Plus className="h-4 w-4" strokeWidth={1.75} /> Plan a trip
          </Button>
        </Link>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-80 rounded-card bg-surface-alt animate-pulse border border-border/40"
            />
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-card p-6 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/60 text-center space-y-2 shadow-card">
          <AlertCircle className="h-6 w-6 text-danger mx-auto" strokeWidth={1.75} />
          <h3 className="text-base font-bold text-danger">Failed to load trips</h3>
          <p className="text-xs text-text-secondary">Please check your connection and try again.</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && trips.length === 0 && (
        <div className="relative rounded-card border-2 border-dashed border-border p-12 text-center max-w-lg mx-auto my-12 space-y-5 bg-surface/60 backdrop-blur-xs">
          <div className="flex justify-center">
            <IconCircle size="lg" color="blue">
              <Compass className="h-6 w-6" strokeWidth={1.75} />
            </IconCircle>
          </div>
          <div className="space-y-1.5">
            <h2 className="text-xl font-bold text-text-primary">
              Plan your first trip
            </h2>
            <p className="text-sm text-text-secondary max-w-sm mx-auto">
              Create a custom itinerary in 60 seconds with live weather monitoring and automatic replans.
            </p>
          </div>
          <div className="pt-2">
            <Link href="/trips/new" className="inline-block">
              <Button variant="primary" className="gap-2 shadow-sm font-semibold">
                <Sparkles className="h-4 w-4" strokeWidth={1.75} /> Plan a trip
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Trip Cards Grid */}
      {!isLoading && !error && trips.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {trips.map((trip) => (
            <TripCard key={trip.id} trip={trip} />
          ))}
        </div>
      )}
    </div>
  );
}
