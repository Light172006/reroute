import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { ItineraryResponse, ItineraryItem } from '@/types/contract';

export function useItinerary(tripId: string) {
  return useQuery({
    queryKey: ['itinerary', tripId],
    queryFn: () => api.getItinerary(tripId),
    enabled: !!tripId,
  });
}

export function useVersions(tripId: string) {
  return useQuery({
    queryKey: ['versions', tripId],
    queryFn: () => api.getVersions(tripId),
    enabled: !!tripId,
  });
}

export function useRestoreVersion(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (versionId: string) => api.restoreVersion(tripId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
      queryClient.invalidateQueries({ queryKey: ['versions', tripId] });
      queryClient.invalidateQueries({ queryKey: ['trip', tripId] });
    },
  });
}

export function useToggleLockItem(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, isLocked }: { itemId: string; isLocked: boolean }) =>
      api.updateItem(itemId, { is_locked: isLocked }),

    // Optimistic update
    onMutate: async ({ itemId, isLocked }) => {
      await queryClient.cancelQueries({ queryKey: ['itinerary', tripId] });
      const previous = queryClient.getQueryData<ItineraryResponse>(['itinerary', tripId]);

      if (previous) {
        const updated: ItineraryResponse = {
          ...previous,
          days: previous.days.map((day) => ({
            ...day,
            items: day.items.map((item) =>
              item.id === itemId ? { ...item, is_locked: isLocked } : item
            ),
          })),
        };
        queryClient.setQueryData(['itinerary', tripId], updated);
      }

      return { previous };
    },

    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['itinerary', tripId], context.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
    },
  });
}

export function useUpdateItem(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, patch }: { itemId: string; patch: Partial<ItineraryItem> }) =>
      api.updateItem(itemId, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
    },
  });
}

export function useDeleteItem(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => api.deleteItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
    },
  });
}

export function useReorderItems(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ dayIndex, orderedKeys }: { dayIndex: number; orderedKeys: string[] }) =>
      api.reorderItems(tripId, dayIndex, orderedKeys),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
    },
  });
}
