'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useTheme } from 'next-themes';
import type L from 'leaflet';
import { ItineraryItem } from '@/types/contract';
import 'leaflet/dist/leaflet.css';

interface MapViewProps {
  items: ItineraryItem[];
  highlightedItemId?: string | null;
  affectedStableKeys?: string[];
  onMarkerClick?: (item: ItineraryItem) => void;
  className?: string;
  daysCount?: number;
  selectedDayIndex?: number;
  onSelectDay?: (day: number) => void;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function MapView({
  items,
  highlightedItemId,
  affectedStableKeys = [],
  onMarkerClick,
  className = '',
  daysCount,
  selectedDayIndex,
  onSelectDay,
}: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const [isClient, setIsClient] = useState(false);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    if (!isClient || !mapContainerRef.current) return;

    let isCancelled = false;

    import('leaflet').then((L) => {
      if (isCancelled || !mapContainerRef.current) return;

      // Clean up previous map if exists
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }

      // Filter valid coordinate items
      const validItems = items.filter(
        (i) => typeof i.lat === 'number' && typeof i.lng === 'number'
      );

      const defaultCenter: [number, number] =
        validItems.length > 0 ? [validItems[0].lat!, validItems[0].lng!] : [27.036, 88.2627];

      const map = L.map(mapContainerRef.current, {
        zoomControl: false,
      }).setView(defaultCenter, 13);
      mapInstanceRef.current = map;

      // Add zoom control at bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // Select tiles based on light / dark mode
      const isDark = resolvedTheme === 'dark';
      const tileUrl = isDark
        ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

      L.tileLayer(tileUrl, {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        maxZoom: 19,
      }).addTo(map);

      const latlngs: [number, number][] = [];

      validItems.forEach((item, index) => {
        const lat = item.lat!;
        const lng = item.lng!;
        latlngs.push([lat, lng]);

        const isAffected = affectedStableKeys.includes(item.stable_key);
        const isHighlighted = item.id === highlightedItemId;

        // Numbered pin marker: Amber if affected, Ultramarine in light / Near-monochrome White in dark
        const markerBg = isAffected
          ? '#F59E0B'
          : isHighlighted
          ? isDark
            ? '#FFFFFF'
            : '#3451D1'
          : isDark
          ? '#FAFAFA'
          : '#4166F5';

        const markerTextColor = isDark && !isAffected ? '#0A0A0A' : '#FFFFFF';
        const ringColor = isDark ? 'rgba(250, 250, 250, 0.40)' : 'rgba(65, 102, 245, 0.40)';

        const markerHtml = `
          <div style="
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background-color: ${markerBg};
            color: ${markerTextColor};
            font-family: inherit;
            font-weight: 700;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid ${isDark ? '#262626' : '#FFFFFF'};
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
            cursor: pointer;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            ${isHighlighted ? `transform: scale(1.2); box-shadow: 0 0 0 4px ${ringColor};` : ''}
          ">
            ${index + 1}
          </div>
        `;

        const icon = L.divIcon({
          html: markerHtml,
          className: 'custom-leaflet-marker',
          iconSize: [32, 32],
          iconAnchor: [16, 16],
          popupAnchor: [0, -18],
        });

        const marker = L.marker([lat, lng], { icon }).addTo(map);

        const safeTitle = escapeHtml(item.title || '');
        marker.bindPopup(`
          <div style="font-family: inherit; font-size: 13px; padding: 4px; line-height: 1.4; background-color: ${isDark ? '#141414' : '#FFFFFF'}; color: ${isDark ? '#FAFAFA' : '#1E293B'};">
            <div style="font-weight: 700; color: ${isDark ? '#FAFAFA' : '#1E293B'};">${index + 1}. ${safeTitle}</div>
            <div style="color: ${isDark ? '#A3A3A3' : '#64748B'}; font-size: 11px; margin-top: 2px;">${item.start_time} - ${item.end_time}</div>
            ${
              isAffected
                ? '<div style="color: #D97706; font-size: 11px; font-weight: 600; margin-top: 4px;">Attention needed (Weather risk)</div>'
                : ''
            }
          </div>
        `);

        marker.on('click', () => {
          onMarkerClick?.(item);
        });
      });

      // Route polyline with primary color and dashed style
      if (latlngs.length > 1) {
        L.polyline(latlngs, {
          color: isDark ? '#D4D4D4' : '#4166F5',
          weight: 4,
          opacity: 0.85,
          dashArray: '6, 8',
        }).addTo(map);

        const bounds = L.latLngBounds(latlngs);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    });

    return () => {
      isCancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isClient, items, highlightedItemId, affectedStableKeys, onMarkerClick, resolvedTheme]);

  if (!isClient) {
    return (
      <div className={`card-surface animate-pulse flex items-center justify-center text-small text-slate-400 ${className}`}>
        Loading interactive map...
      </div>
    );
  }

  return (
    <div className={`relative rounded-card overflow-hidden border border-border shadow-sm ${className}`}>
      {/* Floating Day Selector Chips over the Map */}
      {daysCount && daysCount > 1 && onSelectDay && (
        <div className="absolute top-4 left-4 z-20 flex items-center gap-1.5 glass-surface p-1.5 rounded-pill shadow-md border border-border">
          {Array.from({ length: daysCount }, (_, i) => i + 1).map((d) => (
            <button
              key={d}
              onClick={() => onSelectDay(d)}
              className={`px-3 py-1 rounded-pill text-caption font-semibold transition-all ${
                selectedDayIndex === d
                  ? 'btn-primary-gradient text-white shadow-xs'
                  : 'text-text-secondary hover:bg-surface-alt'
              }`}
            >
              Day {d}
            </button>
          ))}
        </div>
      )}

      <div ref={mapContainerRef} className="w-full h-full min-h-[400px]" />
    </div>
  );
}
