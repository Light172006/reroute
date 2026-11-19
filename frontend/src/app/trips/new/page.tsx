'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { TripWizard } from '@/components/TripWizard';

export default function NewTripPage() {
  const router = useRouter();

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push('/login');
    }
  }, [router]);

  return (
    <div className="flex-1 py-4 sm:py-8">
      <TripWizard />
    </div>
  );
}
