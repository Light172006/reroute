'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { IconCircle } from '@/components/primitives/IconCircle';
import { formatCurrency } from '@/lib/format';
import { api } from '@/lib/api';
import { useUIStore } from '@/hooks/useUIStore';
import { PaceType } from '@/types/contract';
import {
  Compass,
  Calendar,
  Users,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Loader2,
  DollarSign,
  Leaf,
  Scale,
  Zap,
  Check,
  Utensils,
  Building2,
  Mountain,
  Moon,
  ShoppingBag,
} from 'lucide-react';

const tripWizardSchema = z
  .object({
    destination: z.string().min(2, 'Destination is required'),
    title: z.string().optional(),
    start_date: z.string().min(1, 'Start date is required'),
    end_date: z.string().min(1, 'End date is required'),
    group_size: z.coerce.number().min(1, 'At least 1 person'),
    budget_total: z.coerce.number().min(1000, 'Minimum budget is 1,000'),
    budget_per_day_cap: z.coerce.number().optional().nullable(),
    currency: z.string().default('INR'),
    pace: z.enum(['relaxed', 'balanced', 'packed']),
    vibe_tags: z.array(z.string()).min(1, 'Select at least one vibe tag'),
    notes: z.string().optional(),
  })
  .refine((data) => new Date(data.end_date) >= new Date(data.start_date), {
    message: 'End date must be on or after start date',
    path: ['end_date'],
  });

type TripWizardFormValues = z.infer<typeof tripWizardSchema>;

const VIBE_DEFINITIONS = [
  { tag: 'Food', icon: Utensils, label: 'Food & Dining' },
  { tag: 'Culture', icon: Building2, label: 'Culture & Heritage' },
  { tag: 'Nature', icon: Mountain, label: 'Nature & Scenic' },
  { tag: 'Nightlife', icon: Moon, label: 'Nightlife' },
  { tag: 'Shopping', icon: ShoppingBag, label: 'Shopping & Bazaars' },
  { tag: 'Adventure', icon: Compass, label: 'Adventure' },
];

const POPULAR_DESTINATIONS = ['Darjeeling', 'Jaipur', 'Goa', 'Kolkata', 'Manali', 'Udaipur'];

export function TripWizard() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { setActiveRunId } = useUIStore();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TripWizardFormValues>({
    resolver: zodResolver(tripWizardSchema),
    defaultValues: {
      destination: 'Darjeeling',
      title: '',
      start_date: '2026-12-12',
      end_date: '2026-12-15',
      group_size: 2,
      budget_total: 18000,
      budget_per_day_cap: null,
      currency: 'INR',
      pace: 'balanced',
      vibe_tags: ['Nature', 'Food'],
      notes: '',
    },
  });

  const selectedVibes = watch('vibe_tags') || [];
  const currentPace = watch('pace');
  const currentBudget = watch('budget_total');
  const currentCurrency = watch('currency');

  const toggleVibe = (tag: string) => {
    if (selectedVibes.includes(tag)) {
      setValue(
        'vibe_tags',
        selectedVibes.filter((t) => t !== tag),
        { shouldValidate: true }
      );
    } else {
      setValue('vibe_tags', [...selectedVibes, tag], { shouldValidate: true });
    }
  };

  const onSubmit = async (values: TripWizardFormValues) => {
    setIsSubmitting(true);
    try {
      const trip = await api.createTrip({
        title: values.title || `${values.destination} Getaway`,
        destination: values.destination,
        start_date: values.start_date,
        end_date: values.end_date,
        group_size: values.group_size,
        budget_total: values.budget_total,
        budget_per_day_cap: values.budget_per_day_cap || null,
        currency: values.currency,
        pace: values.pace,
        vibe_tags: values.vibe_tags.map((t) => t.toLowerCase()),
        notes: values.notes || null,
      });

      const run = await api.generatePlan(trip.id);
      setActiveRunId(run.run_id);
      router.push(`/trips/${trip.id}?generating=true&run_id=${run.run_id}`);
    } catch (err) {
      console.error('Trip creation failed:', err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      {/* Segmented Progress Bar with Step Labels */}
      <div className="mb-8 space-y-3" aria-label="Wizard Steps">
        <div className="grid grid-cols-3 gap-2">
          {[
            { step: 1, label: 'Where & When' },
            { step: 2, label: 'Budget' },
            { step: 3, label: 'Vibe & Pace' },
          ].map(({ step, label }) => {
            const isCompleted = currentStep > step;
            const isActive = currentStep === step;

            return (
              <div key={step} className="space-y-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    isCompleted || isActive
                      ? 'btn-primary-gradient'
                      : 'bg-surface-alt'
                  }`}
                />
                <span
                  className={`text-caption uppercase tracking-wider block font-semibold ${
                    isActive
                      ? 'text-primary'
                      : isCompleted
                      ? 'text-text-primary'
                      : 'text-text-muted'
                  }`}
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Step 1: Where and When */}
        {currentStep === 1 && (
          <div className="card-surface p-6 sm:p-8 space-y-6">
            <div className="flex items-start gap-4">
              <IconCircle icon={Compass} size="lg" variant="primary" />
              <div className="space-y-1">
                <h2 className="text-h2 font-bold text-text-primary tracking-tight">
                  Where and when are you traveling?
                </h2>
                <p className="text-small text-text-secondary">
                  Select your destination and schedule. Reroute will build a feasible day-by-day sequence.
                </p>
              </div>
            </div>

            <div className="space-y-4 pt-2">
              <div>
                <label htmlFor="destination" className="block text-small font-medium text-text-primary mb-1.5">
                  Destination City
                </label>
                <Input
                  id="destination"
                  aria-label="Destination City"
                  {...register('destination')}
                  placeholder="e.g. Darjeeling, Jaipur, Goa"
                  aria-invalid={!!errors.destination}
                />
                {errors.destination && (
                  <p className="text-caption text-danger mt-1">{errors.destination.message}</p>
                )}
                {/* Popular suggestions */}
                <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                  <span className="text-caption text-text-muted mr-1">Popular:</span>
                  {POPULAR_DESTINATIONS.map((dest) => (
                    <button
                      key={dest}
                      type="button"
                      onClick={() => setValue('destination', dest, { shouldValidate: true })}
                      className="text-caption px-2.5 py-1 rounded-pill bg-surface-alt hover:bg-primary/10 hover:text-primary transition-colors text-text-secondary border border-border"
                    >
                      {dest}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="trip-title" className="block text-small font-medium text-text-primary mb-1.5">
                  Trip Name (Optional)
                </label>
                <Input
                  id="trip-title"
                  aria-label="Trip Name"
                  {...register('title')}
                  placeholder="e.g. Darjeeling Monsoon Getaway"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="start-date" className="block text-small font-medium text-text-primary mb-1.5 flex items-center gap-1.5">
                    <Calendar size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
                    <span>Start Date</span>
                  </label>
                  <Input id="start-date" aria-label="Start Date" type="date" {...register('start_date')} />
                  {errors.start_date && (
                    <p className="text-caption text-danger mt-1">{errors.start_date.message}</p>
                  )}
                </div>
                <div>
                  <label htmlFor="end-date" className="block text-small font-medium text-text-primary mb-1.5 flex items-center gap-1.5">
                    <Calendar size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
                    <span>End Date</span>
                  </label>
                  <Input id="end-date" aria-label="End Date" type="date" {...register('end_date')} />
                  {errors.end_date && (
                    <p className="text-caption text-danger mt-1">{errors.end_date.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="group-size" className="block text-small font-medium text-text-primary mb-1.5 flex items-center gap-1.5">
                  <Users size={16} strokeWidth={1.75} className="text-text-muted" aria-hidden="true" />
                  <span>Number of Travelers</span>
                </label>
                <Input
                  id="group-size"
                  aria-label="Number of Travelers"
                  type="number"
                  min="1"
                  max="20"
                  {...register('group_size')}
                />
                {errors.group_size && (
                  <p className="text-caption text-danger mt-1">{errors.group_size.message}</p>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-border flex justify-end">
              <Button
                type="button"
                onClick={() => setCurrentStep(2)}
                className="gap-2"
              >
                <span>Next: Budget</span>
                <ArrowRight size={16} strokeWidth={1.75} />
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Budget */}
        {currentStep === 2 && (
          <div className="card-surface p-6 sm:p-8 space-y-6">
            <div className="flex items-start gap-4">
              <IconCircle icon={DollarSign} size="lg" variant="primary" />
              <div className="space-y-1">
                <h2 className="text-h2 font-bold text-text-primary tracking-tight">
                  What is your budget?
                </h2>
                <p className="text-small text-text-secondary">
                  Reroute keeps activity costs and dining inside this limit, alerting you before overages happen.
                </p>
              </div>
            </div>

            <div className="space-y-6 pt-2">
              <div className="space-y-3">
                <div className="flex justify-between items-baseline">
                  <label className="text-small font-medium text-text-primary">
                    Total Estimated Budget
                  </label>
                  <span className="tabular-mono text-xl font-bold text-primary bg-primary/10 px-3 py-1 rounded-input border border-primary/20">
                    {formatCurrency(currentBudget, currentCurrency)}
                  </span>
                </div>

                <input
                  type="range"
                  min="3000"
                  max="100000"
                  step="1000"
                  aria-label="Total trip budget"
                  {...register('budget_total')}
                  className="w-full accent-primary h-2 bg-surface-alt rounded-pill cursor-pointer"
                />

                <div className="flex justify-between text-caption text-text-muted tabular-mono">
                  <span>Rs 3,000</span>
                  <span>Rs 50,000</span>
                  <span>Rs 1,00,000+</span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="trip-currency" className="block text-small font-medium text-text-primary mb-1.5">
                    Currency
                  </label>
                  <select
                    id="trip-currency"
                    aria-label="Trip Currency"
                    {...register('currency')}
                    className="w-full h-[40px] rounded-input border border-border bg-surface px-3 text-small text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="INR">INR (₹ - Indian Rupee)</option>
                    <option value="USD">USD ($ - US Dollar)</option>
                    <option value="EUR">EUR (€ - Euro)</option>
                    <option value="GBP">GBP (£ - British Pound)</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="daily-cap" className="block text-small font-medium text-text-primary mb-1.5">
                    Per-day Cap (Optional)
                  </label>
                  <Input
                    id="daily-cap"
                    aria-label="Per-day spending cap"
                    type="number"
                    placeholder="e.g. 5000"
                    {...register('budget_per_day_cap')}
                  />
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(1)}
                className="gap-2"
              >
                <ArrowLeft size={16} strokeWidth={1.75} />
                <span>Back</span>
              </Button>
              <Button
                type="button"
                onClick={() => setCurrentStep(3)}
                className="gap-2"
              >
                <span>Next: Vibe & Pace</span>
                <ArrowRight size={16} strokeWidth={1.75} />
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Vibe & Pace */}
        {currentStep === 3 && (
          <div className="card-surface p-6 sm:p-8 space-y-6">
            <div className="flex items-start gap-4">
              <IconCircle icon={Sparkles} size="lg" variant="primary" />
              <div className="space-y-1">
                <h2 className="text-h2 font-bold text-text-primary tracking-tight">
                  Vibe, Pace & Special Preferences
                </h2>
                <p className="text-small text-text-secondary">
                  Select the atmospheres you love. The AI agent shapes activity pacing accordingly.
                </p>
              </div>
            </div>

            <div className="space-y-6 pt-2">
              {/* Vibe Tags with Icons & Selected Check */}
              <div>
                <label className="block text-small font-medium text-text-primary mb-2.5">
                  Select Vibes (Choose 1 or more)
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {VIBE_DEFINITIONS.map(({ tag, icon: Icon, label }) => {
                    const isSelected = selectedVibes.includes(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleVibe(tag)}
                        className={`flex items-center justify-between p-3 rounded-input text-small font-medium transition-all border text-left ${
                          isSelected
                            ? 'border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary'
                            : 'border-border bg-surface text-text-secondary hover:border-border-muted hover:text-text-primary'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <Icon size={16} strokeWidth={1.75} className={isSelected ? 'text-primary' : 'text-text-muted'} />
                          <span>{label}</span>
                        </span>
                        {isSelected && (
                          <Check size={16} strokeWidth={2} className="text-primary ml-1 shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>
                {errors.vibe_tags && (
                  <p className="text-caption text-danger mt-1.5">{errors.vibe_tags.message}</p>
                )}
              </div>

              {/* Pace Toggle: Segmented Control with Leaf / Scale / Zap icons */}
              <div>
                <label className="block text-small font-medium text-text-primary mb-2">
                  Travel Pace
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'relaxed', label: 'Relaxed', desc: 'Max 8h/day, slow starts', icon: Leaf },
                    { id: 'balanced', label: 'Balanced', desc: 'Max 10h/day, steady flow', icon: Scale },
                    { id: 'packed', label: 'Packed', desc: 'Max 12h/day, see it all', icon: Zap },
                  ].map(({ id, label, desc, icon: PaceIcon }) => {
                    const isSelected = currentPace === id;
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setValue('pace', id as PaceType, { shouldValidate: true })}
                        className={`p-3.5 rounded-input text-left border transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/10 ring-1 ring-primary'
                            : 'border-border bg-surface hover:border-border-muted'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <PaceIcon size={16} strokeWidth={1.75} className={isSelected ? 'text-primary' : 'text-text-muted'} />
                          <span className="text-small font-semibold text-text-primary">
                            {label}
                          </span>
                        </div>
                        <p className="text-caption text-text-muted mt-1">
                          {desc}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-small font-medium text-text-primary mb-1.5">
                  Special Constraints & Notes
                </label>
                <textarea
                  {...register('notes')}
                  rows={3}
                  placeholder="e.g. Vegetarian food preferences, avoid long stair climbs, prioritize tea plantations"
                  className="w-full rounded-input border border-border bg-surface p-3 text-small text-text-primary focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-text-muted transition-colors"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-border flex justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCurrentStep(2)}
                className="gap-2"
                disabled={isSubmitting}
              >
                <ArrowLeft size={16} strokeWidth={1.75} />
                <span>Back</span>
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="gap-2 shadow-sm font-semibold"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
                    <span>Generating itinerary...</span>
                  </>
                ) : (
                  <>
                    <span>Generate My Trip</span>
                    <Sparkles size={16} strokeWidth={1.75} />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
