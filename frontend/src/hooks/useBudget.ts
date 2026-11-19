import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Expense, ExpenseCreate, BudgetSummary } from '@/types/contract';

export function useBudget(tripId: string) {
  return useQuery({
    queryKey: ['budget', tripId],
    queryFn: () => api.getBudget(tripId),
    enabled: !!tripId,
  });
}

export function useExpenses(tripId: string) {
  return useQuery({
    queryKey: ['expenses', tripId],
    queryFn: () => api.getExpenses(tripId),
    enabled: !!tripId,
  });
}

export function useAddExpense(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (expense: ExpenseCreate) => api.addExpense(tripId, expense),

    // Optimistic update for expense list and budget summary
    onMutate: async (newExpense) => {
      await queryClient.cancelQueries({ queryKey: ['expenses', tripId] });
      await queryClient.cancelQueries({ queryKey: ['budget', tripId] });

      const prevExpenses = queryClient.getQueryData<Expense[]>(['expenses', tripId]);
      const prevBudget = queryClient.getQueryData<BudgetSummary>(['budget', tripId]);

      const optimisticExpense: Expense = {
        id: `temp-${Date.now()}`,
        trip_id: tripId,
        user_id: 'usr-current',
        item_stable_key: newExpense.item_stable_key,
        category: newExpense.category,
        amount: newExpense.amount,
        currency: newExpense.currency || 'INR',
        amount_in_trip_currency: newExpense.amount,
        description: newExpense.description,
        spent_at: newExpense.spent_at || new Date().toISOString(),
        created_at: new Date().toISOString(),
      };

      if (prevExpenses) {
        queryClient.setQueryData<Expense[]>(['expenses', tripId], [optimisticExpense, ...prevExpenses]);
      }

      if (prevBudget) {
        const newActual = prevBudget.actual_total + newExpense.amount;
        queryClient.setQueryData<BudgetSummary>(['budget', tripId], {
          ...prevBudget,
          actual_total: newActual,
          remaining: Math.max(0, prevBudget.planned_total - newActual),
          overrun_pct:
            newActual > prevBudget.planned_total
              ? ((newActual - prevBudget.planned_total) / prevBudget.planned_total) * 100
              : 0,
        });
      }

      return { prevExpenses, prevBudget };
    },

    onError: (err, newExpense, context) => {
      if (context?.prevExpenses) {
        queryClient.setQueryData(['expenses', tripId], context.prevExpenses);
      }
      if (context?.prevBudget) {
        queryClient.setQueryData(['budget', tripId], context.prevBudget);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses', tripId] });
      queryClient.invalidateQueries({ queryKey: ['budget', tripId] });
    },
  });
}

export function useDeleteExpense(tripId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteExpense(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses', tripId] });
      queryClient.invalidateQueries({ queryKey: ['budget', tripId] });
    },
  });
}
