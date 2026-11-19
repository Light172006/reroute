import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function usePendingProposals(tripId: string) {
  return useQuery({
    queryKey: ['proposals', tripId, 'pending'],
    queryFn: () => api.getPendingProposals(tripId),
    enabled: !!tripId,
  });
}

export function useProposal(proposalId?: string | null) {
  return useQuery({
    queryKey: ['proposal', proposalId],
    queryFn: () => (proposalId ? api.getProposal(proposalId) : null),
    enabled: !!proposalId,
  });
}

export function useDecideProposal(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      proposalId,
      decision,
      note,
    }: {
      proposalId: string;
      decision: 'approve' | 'reject' | 'alternatives';
      note?: string;
    }) => api.decideProposal(proposalId, decision, note),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['proposals', tripId] });
      queryClient.invalidateQueries({ queryKey: ['trip', tripId] });
      queryClient.invalidateQueries({ queryKey: ['trips'] });
      queryClient.invalidateQueries({ queryKey: ['itinerary', tripId] });
      queryClient.invalidateQueries({ queryKey: ['versions', tripId] });
      return data;
    },
  });
}
