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

const loginSchema = z.object({
  email: z.string().email('Valid email is required'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: 'aarav@reroute.ai',
      password: 'password123',
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.login(data);
      router.push('/trips');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed. Please check your credentials.';
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
            Welcome back
          </h1>
          <p className="text-sm text-text-secondary">
            Sign in to access your self-adapting travel itineraries
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
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-sm font-medium text-text-primary">
                Password
              </label>
            </div>
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
            Sign In <ArrowRight className="h-4 w-4" />
          </Button>
        </form>

        <div className="text-center text-xs text-text-secondary pt-2 border-t border-border">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="font-semibold text-primary hover:underline">
            Sign up
          </Link>
        </div>
      </Card>
    </div>
  );
}
