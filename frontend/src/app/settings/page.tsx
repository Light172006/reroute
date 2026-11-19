'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { useUIStore } from '@/hooks/useUIStore';
import { Settings, Check, Loader2, Gauge } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const { setToast } = useUIStore();
  const [displayName, setDisplayName] = useState('Aarav Mehta');
  const [email, setEmail] = useState('aarav@reroute.ai');
  const [currency, setCurrency] = useState('INR');
  const [units, setUnits] = useState<'metric' | 'imperial'>('metric');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.push('/login');
    }
  }, [router]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setToast({
        type: 'success',
        text: 'Settings updated successfully.',
      });
    }, 600);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8 w-full flex-1 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary flex items-center gap-3">
          <Settings className="h-6 w-6 text-primary" strokeWidth={1.75} />
          Settings & Preferences
        </h1>
        <p className="text-sm text-text-secondary">
          Manage your traveler profile, default currency, and measurement units.
        </p>
      </div>

      <form onSubmit={handleSave}>
        <Card className="p-6 sm:p-8 space-y-6 shadow-card">
          <div className="space-y-5">
            <div>
              <label htmlFor="display-name" className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
                Display Name
              </label>
              <Input
                id="display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your Name"
                className="h-10"
              />
            </div>

            <div>
              <label htmlFor="email-address" className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
                Email Address
              </label>
              <Input
                id="email-address"
                type="email"
                value={email}
                disabled
                className="h-10 bg-surface-alt text-text-muted font-mono text-xs"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-1">
              <div>
                <label htmlFor="home-currency" className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
                  Default Home Currency
                </label>
                <select
                  id="home-currency"
                  aria-label="Default Home Currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full h-10 rounded-input border border-border bg-surface px-3 font-mono text-xs text-text-primary focus:outline-none focus:ring-2 focus:ring-primary shadow-xs"
                >
                  <option value="INR">INR (Rs - Indian Rupee)</option>
                  <option value="USD">USD ($ - US Dollar)</option>
                  <option value="EUR">EUR (€ - Euro)</option>
                  <option value="GBP">GBP (£ - British Pound)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">
                  Measurement Units
                </label>
                <div className="grid grid-cols-2 gap-2 bg-surface-alt p-1 rounded-input border border-border">
                  <button
                    type="button"
                    onClick={() => setUnits('metric')}
                    className={`h-8 rounded-[6px] text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
                      units === 'metric'
                        ? 'bg-surface text-primary shadow-xs'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <Gauge className="h-3.5 w-3.5" strokeWidth={1.75} />
                    Metric (km, °C)
                  </button>
                  <button
                    type="button"
                    onClick={() => setUnits('imperial')}
                    className={`h-8 rounded-[6px] text-xs font-semibold transition-all flex items-center justify-center gap-1.5 ${
                      units === 'imperial'
                        ? 'bg-surface text-primary shadow-xs'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    <Gauge className="h-3.5 w-3.5" strokeWidth={1.75} />
                    Imperial (mi, °F)
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border flex justify-end">
            <Button type="submit" variant="primary" disabled={isSaving} className="gap-2 font-semibold">
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin text-on-primary" strokeWidth={1.75} />
              ) : (
                <Check className="h-4 w-4 text-on-primary" strokeWidth={1.75} />
              )}
              Save Changes
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
