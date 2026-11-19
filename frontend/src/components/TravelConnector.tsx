import React from 'react';
import { TravelInfo, TransportMode } from '@/types/contract';
import { Footprints, Car, Bus, TrainFront, Bike } from 'lucide-react';

interface TravelConnectorProps {
  travel?: TravelInfo | null;
}

const getModeIcon = (mode: TransportMode) => {
  switch (mode) {
    case 'walk':
      return Footprints;
    case 'taxi':
    case 'car':
      return Car;
    case 'bus':
      return Bus;
    case 'train':
    case 'metro':
      return TrainFront;
    case 'bike':
      return Bike;
    default:
      return Car;
  }
};

export function TravelConnector({ travel }: TravelConnectorProps) {
  if (!travel || !travel.minutes) {
    return (
      <div className="h-6 my-1 ml-[5.25rem] border-l-2 border-dashed border-border" />
    );
  }

  const ModeIcon = getModeIcon(travel.mode);

  return (
    <div className="flex items-center gap-3 my-2 ml-16 sm:ml-20 text-caption text-text-muted">
      {/* Dashed line on rail */}
      <div className="flex flex-col items-center">
        <div className="w-0.5 h-3 border-l-2 border-dashed border-border" />
        <div className="h-6 w-6 rounded-full bg-surface-alt text-text-secondary flex items-center justify-center border border-border shadow-xs">
          <ModeIcon size={16} strokeWidth={1.75} aria-hidden="true" />
        </div>
        <div className="w-0.5 h-3 border-l-2 border-dashed border-border" />
      </div>

      {/* Pill with travel details in tabular mono */}
      <div className="tabular-mono text-caption bg-surface-alt px-3 py-1 rounded-pill border border-border flex items-center gap-2">
        <span className="font-bold text-text-primary">
          {travel.minutes} min
        </span>
        <span className="capitalize text-text-secondary">by {travel.mode}</span>
        {travel.distance_m && (
          <span className="text-text-muted">
            • {(travel.distance_m / 1000).toFixed(1)} km
          </span>
        )}
      </div>
    </div>
  );
}
