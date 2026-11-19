'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { ExpenseCreate } from '@/types/contract';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Loader2, PlusCircle } from 'lucide-react';

const expenseSchema = z.object({
  category: z.enum(['stay', 'food', 'transport', 'activities', 'shopping', 'other']),
  amount: z.coerce.number().min(1, 'Amount must be greater than 0'),
  description: z.string().min(2, 'Description is required'),
});

type ExpenseFormData = z.infer<typeof expenseSchema>;

interface ExpenseFormProps {
  onSubmit: (data: ExpenseCreate) => void;
  isSubmitting?: boolean;
  currency?: string;
  className?: string;
}

export function ExpenseForm({
  onSubmit,
  isSubmitting = false,
  currency = 'INR',
  className = '',
}: ExpenseFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExpenseFormData>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      category: 'food',
      amount: 500,
      description: '',
    },
  });

  const handleFormSubmit = (data: ExpenseFormData) => {
    onSubmit({
      ...data,
      currency,
    });
    reset();
  };

  return (
    <form
      onSubmit={handleSubmit(handleFormSubmit)}
      className={`card-surface p-4 sm:p-5 space-y-4 ${className}`}
    >
      <div className="text-caption uppercase tracking-wider text-text-muted font-semibold">
        Log an Expense
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label htmlFor="expense-category" className="block text-caption font-medium text-text-primary mb-1">
            Category
          </label>
          <select
            id="expense-category"
            aria-label="Expense Category"
            {...register('category')}
            className="w-full h-[40px] rounded-input border border-border bg-surface px-3 text-small text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="stay">Stay</option>
            <option value="food">Food</option>
            <option value="transport">Transport</option>
            <option value="activities">Activities</option>
            <option value="shopping">Shopping</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="expense-amount" className="block text-caption font-medium text-text-primary mb-1">
            Amount ({currency})
          </label>
          <Input
            id="expense-amount"
            type="number"
            step="any"
            placeholder="e.g. 850"
            aria-label={`Amount in ${currency}`}
            {...register('amount')}
            className="tabular-mono text-small"
          />
          {errors.amount && (
            <p className="text-caption text-danger mt-1">{errors.amount.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="expense-description" className="block text-caption font-medium text-text-primary mb-1">
            Description
          </label>
          <Input
            id="expense-description"
            placeholder="e.g. Glenary's lunch, Taxi"
            aria-label="Expense description"
            {...register('description')}
            className="text-small"
          />
          {errors.description && (
            <p className="text-caption text-danger mt-1">{errors.description.message}</p>
          )}
        </div>
      </div>

      <div className="flex justify-end pt-1">
        <Button
          type="submit"
          size="sm"
          disabled={isSubmitting}
          className="gap-1.5 shadow-sm font-semibold"
        >
          {isSubmitting ? (
            <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
          ) : (
            <PlusCircle size={16} strokeWidth={1.75} />
          )}
          <span>Add Expense</span>
        </Button>
      </div>
    </form>
  );
}
