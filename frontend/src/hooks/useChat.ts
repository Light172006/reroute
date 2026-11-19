import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useChatHistory(tripId: string) {
  return useQuery({
    queryKey: ['chat', tripId],
    queryFn: () => api.getChatHistory(tripId),
    enabled: !!tripId,
  });
}

export function useSendChat(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (message: string) => api.sendChat(tripId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat', tripId] });
    },
  });
}
