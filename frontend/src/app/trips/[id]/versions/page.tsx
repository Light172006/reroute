'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTrip } from '@/hooks/useTrip';
import { useVersions, useRestoreVersion, useItinerary } from '@/hooks/useItinerary';
import { VersionList } from '@/components/VersionList';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/hooks/useUIStore';
import { ArrowLeft, History, Loader2, ChevronRight } from 'lucide-react';

export default function TripVersionsPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.id as string) || '';

  const { data: trip } = useTrip(tripId);
  const { data: versions = [], isLoading: isVersionsLoading } = useVersions(tripId);
  const { data: itinerary } = useItinerary(tripId);
  const { mutate: restoreVersion, isPending: isRestoring } = useRestoreVersion(tripId);
  const { setToast } = useUIStore();

  const handleRestore = (versionId: string) => {
    restoreVersion(versionId, {
      onSuccess: (data) => {
        setToast({
          type: 'success',
          text: `Itinerary restored to new version v${data.version.version_no}.`,
        });
        router.push(`/trips/${tripId}`);
      },
      onError: () => {
        setToast({
          type: 'error',
          text: 'Failed to restore version.',
        });
      },
    });
  };

  const allVersionDays = React.useMemo(() => {
    if (!itinerary) return {};
    return {
      [itinerary.version.id]: itinerary.days,
    };
  }, [itinerary]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 w-full flex-1 space-y-6">
      {/* Breadcrumb nav */}
      <div className="flex items-center gap-2 text-xs text-text-muted">
        <Link href={`/trips/${tripId}`} className="flex items-center gap-1.5 hover:text-primary transition-colors">
          <ArrowLeft className="h-4 w-4" strokeWidth={1.75} /> Back to workspace
        </Link>
        <ChevronRight className="h-3.5 w-3.5 text-text-muted" strokeWidth={1.75} />
        <span className="font-semibold text-text-primary">
          Version History
        </span>
      </div>

      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary flex items-center gap-3">
          <History className="h-6 w-6 text-primary" strokeWidth={1.75} />
          {trip?.title ? `${trip.title} — History` : 'Version History'}
        </h1>
        <p className="text-sm text-text-secondary">
          Browse and restore previous versions of your itinerary. Every replan is archived safely.
        </p>
      </div>

      {isVersionsLoading ? (
        <div className="p-16 text-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary mx-auto" strokeWidth={1.75} />
        </div>
      ) : (
        <VersionList
          versions={versions}
          currentVersionId={trip?.current_version_id}
          onRestore={handleRestore}
          isRestoring={isRestoring}
          currency={trip?.currency}
          allVersionDays={allVersionDays}
        />
      )}
    </div>
  );
}
