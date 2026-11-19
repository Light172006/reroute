'use client';

import React, { useEffect } from 'react';
import { useUIStore } from '@/hooks/useUIStore';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export function GlobalToast() {
  const { toastMessage, setToast } = useUIStore();

  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 4500);
      return () => clearTimeout(timer);
    }
  }, [toastMessage, setToast]);

  if (!toastMessage) return null;

  const typeConfig = {
    success: {
      icon: CheckCircle2,
      style: 'bg-success-bg border-success-border text-success-text',
      iconClass: 'text-success',
    },
    error: {
      icon: AlertCircle,
      style: 'bg-danger-bg border-danger-border text-danger-text',
      iconClass: 'text-danger',
    },
    warning: {
      icon: AlertTriangle,
      style: 'bg-accent-bg border-accent-border text-accent-text',
      iconClass: 'text-accent',
    },
    info: {
      icon: Info,
      style: 'bg-primary-50 border-primary-200 text-text-primary',
      iconClass: 'text-primary',
    },
  };

  const config = typeConfig[toastMessage.type] || typeConfig.info;
  const Icon = config.icon;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:bottom-6 z-50 flex max-w-md items-center gap-3 rounded-card border p-4 shadow-xl animate-fade-up ${config.style}`}
    >
      <Icon size={20} strokeWidth={1.75} className={`shrink-0 ${config.iconClass}`} aria-hidden="true" />
      <p className="text-small font-medium flex-1 text-text-primary">{toastMessage.text}</p>
      <button
        onClick={() => setToast(null)}
        className="p-1 rounded-full text-text-muted hover:text-text-primary transition-colors"
        aria-label="Dismiss notification"
      >
        <X size={16} strokeWidth={1.75} />
      </button>
    </div>
  );
}
