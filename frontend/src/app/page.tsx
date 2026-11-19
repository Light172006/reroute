import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { IconCircle } from '@/components/primitives/IconCircle';
import {
  Compass,
  Eye,
  RefreshCw,
  Sparkles,
  ArrowRight,
  CloudRain,
  CheckCircle2,
  Lock,
  MinusCircle,
  PlusCircle,
  ShieldCheck,
  Zap,
  Calendar,
  Check,
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="flex-1 flex flex-col w-full overflow-hidden">
      {/* Hero Section */}
      <section className="relative pt-12 pb-20 sm:pt-20 sm:pb-28">
        {/* Soft background decorative blobs */}
        <div
          className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 -z-10 h-96 w-[700px] rounded-full bg-gradient-to-tr from-primary/15 via-[var(--primary-gradient-to)]/15 to-transparent blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute top-48 right-10 -z-10 h-80 w-80 rounded-full bg-amber-400/10 blur-3xl"
          aria-hidden="true"
        />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary/10 text-primary border border-primary/20 text-xs font-semibold shadow-xs">
            <Sparkles className="h-4 w-4 text-primary" strokeWidth={1.75} />
            <span>Agentic AI Travel Companion</span>
          </div>

          <h1 className="text-display sm:text-6xl font-bold tracking-tight text-text-primary max-w-4xl mx-auto leading-tight sm:leading-none">
            A trip plan that <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-[var(--primary-gradient-to)]">fixes itself</span>.
          </h1>

          <p className="text-body sm:text-lg text-text-secondary max-w-2xl mx-auto font-normal leading-relaxed">
            Reroute builds your itinerary, monitors live weather, opening hours, delays, and budget burn — and proposes smart replans before your trip derails.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/trips/new" className="w-full sm:w-auto">
              <Button size="lg" variant="primary" className="w-full sm:w-auto gap-2 shadow-md text-base px-8 font-semibold">
                Plan a trip <ArrowRight className="h-4 w-4" strokeWidth={1.75} />
              </Button>
            </Link>
            <Link href="/trips" className="w-full sm:w-auto">
              <Button variant="outline" size="lg" className="w-full sm:w-auto text-base">
                View My Trips
              </Button>
            </Link>
          </div>

          {/* Product Mockup in Device Frame with Overlapping Disruption Card */}
          <div className="pt-12 max-w-4xl mx-auto relative">
            {/* Device frame */}
            <div className="rounded-[20px] border border-border bg-surface shadow-2xl overflow-hidden text-left">
              {/* Window header */}
              <div className="px-4 py-3 bg-surface-alt border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-border" />
                  <div className="h-3 w-3 rounded-full bg-border" />
                  <div className="h-3 w-3 rounded-full bg-border" />
                </div>
                <div className="h-6 px-4 rounded-full bg-surface border border-border text-[11px] font-mono text-text-secondary flex items-center gap-1.5">
                  <Compass className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
                  reroute.ai/trips/darjeeling-autumn
                </div>
                <div className="w-12" />
              </div>

              {/* Mockup Workspace Content */}
              <div className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-12 gap-6 bg-surface-alt">
                {/* Mock Day Nav */}
                <div className="hidden sm:block sm:col-span-3 space-y-2">
                  <div className="p-2.5 rounded-[10px] bg-surface border border-border text-xs font-semibold flex items-center justify-between">
                    <span>Day 1 • Mall Road</span>
                    <span className="font-mono text-[10px] text-text-muted">Rs 1,200</span>
                  </div>
                  <div className="p-2.5 rounded-[10px] bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-800 text-xs font-semibold flex items-center justify-between text-amber-900 dark:text-amber-200">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                      <span>Day 2 • Outdoor</span>
                    </div>
                    <span className="font-mono text-[10px]">Rs 2,400</span>
                  </div>
                  <div className="p-2.5 rounded-[10px] bg-surface border border-border text-xs font-semibold flex items-center justify-between">
                    <span>Day 3 • Tiger Hill</span>
                    <span className="font-mono text-[10px] text-text-muted">Rs 800</span>
                  </div>
                </div>

                {/* Mock Itinerary items */}
                <div className="col-span-12 sm:col-span-9 space-y-3">
                  <div className="p-3.5 rounded-card bg-surface border border-border shadow-xs flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-text-muted font-medium">09:00</span>
                      <IconCircle size="sm" color="blue">
                        <Compass className="h-4 w-4" strokeWidth={1.75} />
                      </IconCircle>
                      <div>
                        <div className="font-semibold text-text-primary">
                          Ghoom Monastery & Peace Pagoda
                        </div>
                        <div className="text-[11px] text-text-muted">Culture • 90 min</div>
                      </div>
                    </div>
                    <span className="font-mono font-medium text-text-secondary">Rs 200</span>
                  </div>

                  <div className="p-3.5 rounded-card bg-surface border border-border shadow-xs flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-text-muted font-medium">11:30</span>
                      <IconCircle size="sm" color="orange">
                        <Compass className="h-4 w-4" strokeWidth={1.75} />
                      </IconCircle>
                      <div>
                        <div className="font-semibold text-text-primary">
                          Keventers Terrace Breakfast
                        </div>
                        <div className="text-[11px] text-text-muted">Food • 60 min</div>
                      </div>
                    </div>
                    <span className="font-mono font-medium text-text-secondary">Rs 650</span>
                  </div>

                  <div className="p-3.5 rounded-card bg-surface border border-dashed border-border-strong shadow-xs flex items-center justify-between text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-text-muted font-medium">14:00</span>
                      <IconCircle size="sm" color="green">
                        <Compass className="h-4 w-4" strokeWidth={1.75} />
                      </IconCircle>
                      <div>
                        <div className="font-semibold text-text-primary">
                          Happy Valley Tea Estate
                        </div>
                        <div className="text-[11px] text-text-muted">Outdoor • 120 min</div>
                      </div>
                    </div>
                    <span className="font-mono font-medium text-text-secondary">Rs 500</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Overlapping Floating Amber Disruption Card */}
            <div className="sm:absolute sm:-bottom-8 sm:right-6 sm:max-w-md w-full mt-4 sm:mt-0 z-20">
              <div className="rounded-card bg-amber-50 dark:bg-amber-950/90 border border-amber-300 dark:border-amber-700/80 p-4 shadow-xl text-left space-y-3 backdrop-blur-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <IconCircle size="sm" color="orange">
                      <CloudRain className="h-4 w-4 text-accent" strokeWidth={1.75} />
                    </IconCircle>
                    <span className="text-xs font-bold text-amber-900 dark:text-amber-200">
                      Disruption detected: Rain (80%)
                    </span>
                  </div>
                  <Badge variant="accent" className="text-[10px] font-semibold">
                    Day 2 Replan
                  </Badge>
                </div>

                <p className="text-xs text-amber-800/90 dark:text-amber-300/90 leading-relaxed">
                  Rain expected 2-6pm. 2 outdoor stops swapped for indoor cultural venues nearby.
                </p>

                {/* Diff preview */}
                <div className="space-y-1.5 pt-1 text-xs">
                  <div className="p-2 rounded-[8px] bg-red-100/60 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MinusCircle className="h-3.5 w-3.5 text-danger" strokeWidth={1.75} />
                      <span className="line-through text-text-secondary font-medium truncate max-w-[200px]">
                        Happy Valley Tea Estate
                      </span>
                    </div>
                    <span className="font-mono text-red-700 dark:text-red-300 text-[11px] font-semibold">Outdoor</span>
                  </div>

                  <div className="p-2 rounded-[8px] bg-green-100/60 dark:bg-green-950/40 border border-green-200 dark:border-green-900/60 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PlusCircle className="h-3.5 w-3.5 text-success" strokeWidth={1.75} />
                      <span className="text-text-primary font-semibold truncate max-w-[200px]">
                        Himalayan Museum & Indoor Gallery
                      </span>
                    </div>
                    <span className="font-mono text-green-700 dark:text-green-300 text-[11px] font-bold">-Rs 150</span>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-between border-t border-amber-200 dark:border-amber-800/60">
                  <span className="text-[11px] font-mono text-amber-900 dark:text-amber-200 font-medium">
                    1 stop changed • User approval required
                  </span>
                  <Link href="/trips/darjeeling-sample">
                    <Button size="sm" variant="primary" className="h-7 text-xs font-semibold px-3">
                      Review changes
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3-Step "How It Works" Strip with Dashed Connector */}
      <section className="py-16 sm:py-24 border-t border-border bg-surface-alt">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary">
              How Reroute Works
            </h2>
            <p className="text-sm text-text-muted">
              Three autonomous pillars that turn initial travel ideas into a flexible journey that survives reality.
            </p>
          </div>

          <div className="relative grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Dashed connector line across steps */}
            <div
              className="hidden md:block absolute top-12 left-1/6 right-1/6 h-0.5 border-t-2 border-dashed border-border -z-0"
              aria-hidden="true"
            />

            {/* Step 1 */}
            <div className="relative z-10 text-center space-y-4">
              <div className="mx-auto">
                <IconCircle size="lg" color="blue" className="mx-auto ring-8 ring-surface-alt">
                  <Compass className="h-6 w-6" strokeWidth={1.75} />
                </IconCircle>
              </div>
              <h3 className="text-lg font-bold text-text-primary">
                1. Plan
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed max-w-xs mx-auto">
                Set destination, budget, group size, and vibe. The AI synthesizes opening hours, distance, and daily caps into an optimal itinerary.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative z-10 text-center space-y-4">
              <div className="mx-auto">
                <IconCircle size="lg" color="orange" className="mx-auto ring-8 ring-surface-alt">
                  <Eye className="h-6 w-6 text-accent" strokeWidth={1.75} />
                </IconCircle>
              </div>
              <h3 className="text-lg font-bold text-text-primary">
                2. Watch
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed max-w-xs mx-auto">
                Real travel encounters rain, closures, transit lags, and overspending. Reroute monitors live external signals continuously.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative z-10 text-center space-y-4">
              <div className="mx-auto">
                <IconCircle size="lg" color="green" className="mx-auto ring-8 ring-surface-alt">
                  <RefreshCw className="h-6 w-6 text-success" strokeWidth={1.75} />
                </IconCircle>
              </div>
              <h3 className="text-lg font-bold text-text-primary">
                3. Reroute
              </h3>
              <p className="text-sm text-text-secondary leading-relaxed max-w-xs mx-auto">
                When a disruption occurs, the agent crafts targeted swaps. Review a clear before/after diff and approve or reject with one tap.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Detailed Feature Cards */}
      <section className="py-16 sm:py-24 max-w-7xl mx-auto px-4 sm:px-6 w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1 */}
          <Card className="p-6 sm:p-8 space-y-4 shadow-card hover:shadow-card-hover transition-all">
            <IconCircle size="md" color="blue">
              <Compass className="h-5 w-5" strokeWidth={1.75} />
            </IconCircle>
            <h3 className="text-lg font-bold text-text-primary">
              Intelligent Synthesis
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              No generic top-10 lists. Every stop is validated for opening hours, geo-cluster routing, and realistic travel buffers.
            </p>
            <ul className="text-xs text-text-muted space-y-2 pt-3 border-t border-border">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" strokeWidth={1.75} /> Realistic transit time calculation
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" strokeWidth={1.75} /> Daily budget envelope management
              </li>
            </ul>
          </Card>

          {/* Card 2 */}
          <Card className="p-6 sm:p-8 space-y-4 shadow-card hover:shadow-card-hover transition-all">
            <IconCircle size="md" color="orange">
              <CloudRain className="h-5 w-5 text-accent" strokeWidth={1.75} />
            </IconCircle>
            <h3 className="text-lg font-bold text-text-primary">
              Active Disruption Radar
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              Monitors rain forecasts, unexpected temple closures, train delays, and currency spikes before you arrive at locked gates.
            </p>
            <ul className="text-xs text-text-muted space-y-2 pt-3 border-t border-border">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" strokeWidth={1.75} /> Live weather precipitation alerts
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" strokeWidth={1.75} /> Real-time expense vs budget tracker
              </li>
            </ul>
          </Card>

          {/* Card 3 */}
          <Card className="p-6 sm:p-8 space-y-4 shadow-card hover:shadow-card-hover transition-all">
            <IconCircle size="md" color="green">
              <ShieldCheck className="h-5 w-5 text-success" strokeWidth={1.75} />
            </IconCircle>
            <h3 className="text-lg font-bold text-text-primary">
              Human-in-the-Loop Control
            </h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              The agent never silently edits your plans. You review crystal-clear diffs, request alternatives, and lock non-negotiable stops.
            </p>
            <ul className="text-xs text-text-muted space-y-2 pt-3 border-t border-border">
              <li className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-primary" strokeWidth={1.75} /> Locked items remain strictly untouched
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" strokeWidth={1.75} /> Full snapshot version history with undo
              </li>
            </ul>
          </Card>
        </div>
      </section>

      {/* CTA Band */}
      <section className="relative overflow-hidden py-16 px-4 sm:px-6 bg-gradient-to-r from-primary to-[var(--primary-gradient-to)] dark:from-surface-alt dark:to-surface-alt dark:border-y dark:border-border text-on-primary dark:text-text-primary text-center">
        <div className="max-w-4xl mx-auto space-y-6">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-on-primary dark:text-text-primary">
            Ready to travel without the anxiety of broken plans?
          </h2>
          <p className="text-on-primary/90 dark:text-text-secondary text-base sm:text-lg max-w-xl mx-auto">
            Create your itinerary in 60 seconds and let Reroute keep watch while you enjoy the journey.
          </p>
          <div className="pt-2">
            <Link href="/trips/new">
              <Button size="lg" className="bg-surface text-text-primary hover:bg-surface-alt dark:bg-primary dark:text-on-primary dark:hover:bg-primary-hover shadow-lg text-base px-8 font-semibold">
                Plan a trip now <ArrowRight className="h-4 w-4 ml-2" strokeWidth={1.75} />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Minimal Footer */}
      <footer className="mt-auto border-t border-border py-8 bg-surface text-xs text-text-muted">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Compass className="h-4 w-4 text-primary" strokeWidth={1.75} />
            <span className="font-semibold text-text-primary">Reroute</span>
            <span>— Agentic AI travel companion</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-text-muted">
            <span>Inter (UI) & JetBrains Mono</span>
            <span>•</span>
            <span>WCAG AA Accessible</span>
            <span>•</span>
            <span>Human-in-the-Loop</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
