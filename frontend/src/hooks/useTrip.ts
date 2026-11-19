import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Trip, TripCreate } from '@/types/contract';

export function useTrips() {
  return useQuery({
    queryKey: ['trips'],
    queryFn: () => api.getTrips(),
  });
}

export function useTrip(tripId: string) {
  return useQuery({
    queryKey: ['trip', tripId],
    queryFn: () => api.getTrip(tripId),
    enabled: !!tripId,
  });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TripCreate) => api.createTrip(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

export function useUpdateTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Trip> }) =>
      api.updateTrip(id, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['trip', vars.id] });
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

export function useDeleteTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteTrip(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}
