'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { GlassBar } from '@/components/primitives/GlassBar';
import { api } from '@/lib/api';
import {
  Route,
  MapPin,
  Settings,
  Sun,
  Moon,
  LogOut,
  Plus,
} from 'lucide-react';

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  const [isAuthed, setIsAuthed] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    setIsAuthed(api.isAuthenticated());
  }, []);

  const isAuthPage = pathname === '/login' || pathname === '/signup';
  const isLanding = pathname === '/';

  const handleLogout = () => {
    api.clearTokens();
    router.push('/login');
  };

  return (
    <GlassBar position="top" border="bottom">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Wordmark with Route icon */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-[10px] btn-primary-gradient flex items-center justify-center text-white shadow-sm group-hover:shadow-md transition-shadow">
            <Route size={20} strokeWidth={1.75} aria-hidden="true" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-h3 font-bold tracking-tight text-text-primary">
              Reroute
            </span>
            <span className="text-caption uppercase px-1.5 py-0.5 rounded-pill bg-primary/10 text-primary font-semibold border border-primary/20">
              Agent
            </span>
          </div>
        </Link>

        {/* Center Navigation Links (if authenticated) */}
        {!isAuthPage && (
          <nav className="hidden md:flex items-center gap-1">
            <Link
              href="/trips"
              className={`px-3.5 py-2 rounded-input text-small font-medium transition-colors flex items-center gap-2 ${
                pathname.startsWith('/trips')
                  ? 'bg-primary/10 text-primary font-semibold'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-alt'
              }`}
            >
              <MapPin size={16} strokeWidth={1.75} />
              <span>My Trips</span>
            </Link>
            <Link
              href="/settings"
              className={`px-3.5 py-2 rounded-input text-small font-medium transition-colors flex items-center gap-2 ${
                pathname === '/settings'
                  ? 'bg-primary/10 text-primary font-semibold'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-alt'
              }`}
            >
              <Settings size={16} strokeWidth={1.75} />
              <span>Settings</span>
            </Link>
          </nav>
        )}

        {/* Right side controls */}
        <div className="flex items-center gap-2">
          {/* Dark mode toggle */}
          {mounted && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="Toggle light and dark color theme"
              className="text-text-muted hover:text-text-primary"
            >
              {theme === 'dark' ? (
                <Sun size={20} strokeWidth={1.75} />
              ) : (
                <Moon size={20} strokeWidth={1.75} />
              )}
            </Button>
          )}

          {isAuthPage ? null : !mounted || (isLanding && !isAuthed) ? (
            <div className="flex items-center gap-2">
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="sm">
                  Sign up
                </Button>
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/trips/new" className="hidden sm:inline-flex">
                <Button variant="primary" size="sm" className="gap-1.5 shadow-sm">
                  <Plus size={16} strokeWidth={1.75} />
                  <span>Plan a trip</span>
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleLogout}
                aria-label="Sign out of Reroute"
                className="text-text-muted hover:text-danger hover:bg-danger-bg"
              >
                <LogOut size={20} strokeWidth={1.75} />
              </Button>
            </div>
          )}
        </div>
      </div>
    </GlassBar>
  );
}
