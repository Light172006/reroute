import * as React from 'react';
import { X } from 'lucide-react';
import { Button } from './button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  isBottomSheetOnMobile?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  isBottomSheetOnMobile = true,
}: ModalProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-0 md:p-6 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`relative z-10 w-full glass-surface shadow-2xl border border-border transition-all flex flex-col max-h-[90vh] ${
          isBottomSheetOnMobile
            ? 'mt-auto md:mt-0 rounded-t-[20px] md:rounded-[16px] md:max-w-2xl lg:max-w-3xl'
            : 'rounded-[16px] max-w-2xl'
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border p-5 sm:p-6">
          <div className="space-y-1">
            <h2 id="modal-title" className="text-h2 font-bold text-text-primary tracking-tight">
              {title}
            </h2>
            {description && (
              <p className="text-small text-text-secondary">
                {description}
              </p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            aria-label="Close modal"
            className="text-text-muted hover:text-text-primary ml-4 shrink-0"
          >
            <X size={20} strokeWidth={1.75} />
          </Button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-5 sm:p-6 flex-1 space-y-4">{children}</div>
      </div>
    </div>
  );
}
