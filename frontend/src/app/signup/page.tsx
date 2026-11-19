'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Compass, Loader2, ArrowRight } from 'lucide-react';

const signupSchema = z.object({
  display_name: z.string().min(2, 'Name is required'),
  email: z.string().email('Valid email is required'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      display_name: 'Meera Rao',
      email: 'meera@reroute.ai',
      password: 'password123',
    },
  });

  const onSubmit = async (data: SignupFormValues) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.signup(data);
      router.push('/trips');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Signup failed. Please try again.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6 sm:p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 rounded-[12px] bg-primary items-center justify-center text-on-primary shadow-sm mb-1">
            <Compass className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            Create an account
          </h1>
          <p className="text-sm text-text-secondary">
            Start planning with AI itineraries that handle disruptions automatically
          </p>
        </div>

        {error && (
          <div className="p-3 rounded-[8px] bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-danger font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Full Name
            </label>
            <Input
              placeholder="e.g. Meera Rao"
              {...register('display_name')}
              aria-invalid={!!errors.display_name}
            />
            {errors.display_name && (
              <p className="text-xs text-danger mt-1">{errors.display_name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Email Address
            </label>
            <Input
              type="email"
              placeholder="you@domain.com"
              {...register('email')}
              aria-invalid={!!errors.email}
            />
            {errors.email && (
              <p className="text-xs text-danger mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-1.5">
              Password
            </label>
            <Input
              type="password"
              placeholder="••••••••"
              {...register('password')}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <p className="text-xs text-danger mt-1">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" disabled={isLoading} className="w-full gap-2 mt-2">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create Account <ArrowRight className="h-4 w-4" />
          </Button>
        </form>

        <div className="text-center text-xs text-text-secondary pt-2 border-t border-border">
          Already have an account?{' '}
          <Link href="/login" className="font-semibold text-primary hover:underline">
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  );
}
