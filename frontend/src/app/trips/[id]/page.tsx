'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { useTrip } from '@/hooks/useTrip';
import {
  useItinerary,
  useToggleLockItem,
  useDeleteItem,
  useReorderItems,
} from '@/hooks/useItinerary';
import { usePendingProposals } from '@/hooks/useProposal';
import { useBudget, useExpenses, useAddExpense, useDeleteExpense } from '@/hooks/useBudget';
import { useRunStream } from '@/hooks/useRunStream';
import { useUIStore } from '@/hooks/useUIStore';
import { api } from '@/lib/api';
import { formatDateRange, formatCurrency } from '@/lib/format';
import { ItineraryItem } from '@/types/contract';

import { DayNav } from '@/components/DayNav';
import { ItineraryItemCard } from '@/components/ItineraryItemCard';
import { TravelConnector } from '@/components/TravelConnector';
import { DaySummary } from '@/components/DaySummary';
import { DisruptionBanner } from '@/components/DisruptionBanner';
import { ProposalSheet } from '@/components/ProposalSheet';
import { AgentTimeline } from '@/components/AgentTimeline';
import { AgentChat } from '@/components/AgentChat';
import { BudgetBar } from '@/components/BudgetBar';
import { BudgetDonutChart } from '@/components/BudgetDonutChart';
import { ExpenseForm } from '@/components/ExpenseForm';
import { MapView } from '@/components/MapView';
import { SimulateMenu } from '@/components/SimulateMenu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { IconCircle } from '@/components/primitives/IconCircle';

import {
  CheckCircle,
  AlertTriangle,
  History,
  Bot,
  Map as MapIcon,
  DollarSign,
  PanelRightClose,
  PanelRightOpen,
  WifiOff,
  RotateCcw,
  RefreshCw,
  Trash2,
  Loader2,
  Calendar,
  ChevronRight,
  Compass,
  Utensils,
  Landmark,
  Trees,
  PartyPopper,
  ShoppingBag,
  Sparkles,
  Bus,
  LucideIcon,
} from 'lucide-react';

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  sightseeing: Compass,
  food: Utensils,
  culture: Landmark,
  nature: Trees,
  nightlife: PartyPopper,
  shopping: ShoppingBag,
  adventure: Sparkles,
  transport: Bus,
};

interface SortableItineraryItemProps {
  item: ItineraryItem;
  currency?: string;
  isHighlighted?: boolean;
  isAffected?: boolean;
  onToggleLock: (locked: boolean) => void;
  onDelete: () => void;
  onEdit?: (item: ItineraryItem) => void;
}

// Draggable Sortable Item Wrapper
function SortableItineraryItem({
  item,
  currency,
  isHighlighted,
  isAffected,
  onToggleLock,
  onDelete,
  onEdit,
}: SortableItineraryItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.stable_key,
    disabled: item.is_locked,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 20 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <ItineraryItemCard
        item={item}
        currency={currency}
        isHighlighted={isHighlighted}
        isAffectedByProposal={isAffected}
        onToggleLock={onToggleLock}
        onDelete={onDelete}
        onEdit={onEdit}
        dragHandleProps={{ ...attributes, ...listeners }}
      />
    </div>
  );
}

export default function TripWorkspacePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const tripId = (params?.id as string) || '';

  const initialRunId = searchParams.get('run_id');
  const isGeneratingParam = searchParams.get('generating') === 'true';

  const {
    selectedDayIndex,
    setSelectedDayIndex,
    activeTab,
    setActiveTab,
    isAgentPanelOpen,
    toggleAgentPanel,
    isProposalSheetOpen,
    setProposalSheetOpen,
    highlightedItemId,
    setHighlightedItemId,
    activeRunId,
    setActiveRunId,
    setToast,
  } = useUIStore();

  const [isOffline, setIsOffline] = useState(false);
  const [isCheckingPlan, setIsCheckingPlan] = useState(false);

  // Queries
  const { data: trip, isLoading: isTripLoading } = useTrip(tripId);
  const { data: itinerary, isLoading: isItinLoading } = useItinerary(tripId);
  const { data: pendingProposals = [] } = usePendingProposals(tripId);
  const { data: budgetData } = useBudget(tripId);
  const { data: expensesList = [] } = useExpenses(tripId);

  // Mutations
  const toggleLockMutation = useToggleLockItem(tripId);
  const deleteItemMutation = useDeleteItem(tripId);
  const reorderMutation = useReorderItems(tripId);
  const addExpenseMutation = useAddExpense(tripId);
  const deleteExpenseMutation = useDeleteExpense(tripId);

  // Active pending proposal
  const activeProposal = pendingProposals[0] || null;

  // Stream Hook
  const {
    events: streamEvents,
    isRunning: isStreamRunning,
    streamingText,
    error: streamError,
    retry: retryStream,
  } = useRunStream(activeRunId || initialRunId, {
    tripId,
    onProposal: () => {
      setToast({
        type: 'warning',
        text: 'New replan proposal available for review!',
      });
    },
    onDone: () => {
      setActiveRunId(null);
    },
  });

  useEffect(() => {
    if (initialRunId && !activeRunId) {
      setActiveRunId(initialRunId);
    }
  }, [initialRunId, activeRunId, setActiveRunId]);

  // Offline listener
  useEffect(() => {
    setIsOffline(!navigator.onLine);
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // DnD Sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // Selected Day Data
  const currentDay = useMemo(() => {
    if (!itinerary?.days) return null;
    return (
      itinerary.days.find((d) => d.day_index === selectedDayIndex) ||
      itinerary.days[0] ||
      null
    );
  }, [itinerary, selectedDayIndex]);

  // Affected stable keys from pending proposal
  const affectedKeys = useMemo(() => {
    if (!activeProposal) return [];
    const keys: string[] = [];
    if (activeProposal.diff) {
      activeProposal.diff.forEach((d) => keys.push(d.stable_key));
    }
    return keys;
  }, [activeProposal]);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !currentDay) return;

    const oldIndex = currentDay.items.findIndex((item) => item.stable_key === active.id);
    const newIndex = currentDay.items.findIndex((item) => item.stable_key === over.id);

    if (oldIndex !== -1 && newIndex !== -1) {
      const newItems = arrayMove(currentDay.items, oldIndex, newIndex);
      const orderedKeys = newItems.map((i) => i.stable_key);
      reorderMutation.mutate({
        dayIndex: currentDay.day_index,
        orderedKeys,
      });
    }
  };

  const handleCheckPlanNow = async () => {
    setIsCheckingPlan(true);
    try {
      const res = await api.checkPlan(tripId);
      setActiveRunId(res.run_id);
    } catch (err) {
      console.error(err);
    } finally {
      setIsCheckingPlan(false);
    }
  };

  const isGenerating = isStreamRunning && (isGeneratingParam || !itinerary?.days?.length);

  return (
    <div className="flex-1 flex flex-col w-full">
      {/* Offline Alert Bar */}
      {isOffline && (
        <div className="bg-surface-alt text-text-primary text-xs py-2 px-4 flex items-center justify-center gap-2 border-b border-border">
          <WifiOff className="h-4 w-4 text-accent" strokeWidth={1.75} />
          <span>Offline mode. Viewing cached itinerary. Changes will sync when reconnected.</span>
          <Badge variant="accent" className="py-0 text-[10px]">
            Offline
          </Badge>
        </div>
      )}

      {/* Sticky Glass Workspace Sub-header */}
      <div className="sticky top-16 z-20 bg-surface/85 backdrop-blur-md border-b border-border px-4 sm:px-6 py-3.5 transition-all">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="space-y-1">
            {/* Breadcrumb row */}
            <div className="flex items-center gap-2 text-xs text-text-secondary">
              <Link href="/trips" className="hover:text-primary transition-colors">
                My Trips
              </Link>
              <ChevronRight className="h-3.5 w-3.5" strokeWidth={1.75} />
              <span className="font-semibold text-text-primary truncate max-w-[200px] sm:max-w-xs">
                {trip?.title || 'Trip Workspace'}
              </span>
              {trip?.current_version_id && (
                <Link href={`/trips/${tripId}/versions`}>
                  <Badge
                    variant="secondary"
                    className="hover:bg-surface-alt transition-colors gap-1 font-mono text-[11px]"
                  >
                    <History className="h-3.5 w-3.5" strokeWidth={1.75} />
                    v{itinerary?.version?.version_no || 1}
                  </Badge>
                </Link>
              )}
            </div>

            <div className="flex flex-wrap items-center text-xs text-text-secondary gap-2 sm:gap-3">
              <span className="font-semibold text-text-primary">
                {trip?.destination}
              </span>
              <span>•</span>
              <span>{trip ? formatDateRange(trip.start_date, trip.end_date) : ''}</span>
              <span>•</span>
              <span className="capitalize">{trip?.pace} pace</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleCheckPlanNow}
              disabled={isCheckingPlan || isStreamRunning}
              className="gap-2 text-xs font-semibold shadow-xs"
            >
              {isCheckingPlan || isStreamRunning ? (
                <Loader2 className="h-4 w-4 animate-spin text-white" strokeWidth={1.75} />
              ) : (
                <RefreshCw className="h-4 w-4 text-white" strokeWidth={1.75} />
              )}
              Check my plan now
            </Button>

            <SimulateMenu
              tripId={tripId}
              onSimulateStarted={(runId) => {
                setActiveRunId(runId);
                setToast({
                  type: 'info',
                  text: 'Simulating disruption signal...',
                });
              }}
            />

            <Button
              variant="ghost"
              size="icon"
              onClick={toggleAgentPanel}
              aria-label={isAgentPanelOpen ? 'Collapse agent panel' : 'Open agent panel'}
              className="hidden lg:inline-flex text-text-muted hover:text-text-primary"
            >
              {isAgentPanelOpen ? (
                <PanelRightClose className="h-5 w-5" strokeWidth={1.75} />
              ) : (
                <PanelRightOpen className="h-5 w-5" strokeWidth={1.75} />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex flex-col gap-6">
        {/* Disruption Banner if pending proposal exists */}
        {activeProposal && (
          <DisruptionBanner
            proposal={activeProposal}
            onReview={() => setProposalSheetOpen(true)}
          />
        )}

        {/* State Banners */}
        {streamError && (
          <div className="p-4 rounded-card bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/60 text-xs text-danger flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="h-4 w-4 shrink-0" strokeWidth={1.75} />
              <span className="font-medium">{streamError}</span>
            </div>
            <Button size="sm" variant="outline" onClick={retryStream} className="h-8 text-xs font-semibold">
              <RotateCcw className="h-3.5 w-3.5 mr-1.5" strokeWidth={1.75} /> Retry
            </Button>
          </div>
        )}

        {!activeProposal && !isStreamRunning && !streamError && (
          <div className="p-3.5 rounded-card bg-green-50/70 dark:bg-green-950/20 border border-green-200/80 dark:border-green-900/40 flex items-center justify-between text-xs text-green-900 dark:text-green-200 shadow-xs">
            <div className="flex items-center gap-2.5">
              <CheckCircle className="h-4 w-4 text-success shrink-0" strokeWidth={1.75} />
              <span className="font-semibold">
                Plan looks good. All constraints satisfied.
              </span>
            </div>
            <span className="text-[11px] font-mono text-green-700 dark:text-green-400">
              0 conflicts • Weather optimal
            </span>
          </div>
        )}

        {/* Mobile Horizontal Day Selector Chips */}
        {itinerary?.days && (
          <DayNav
            days={itinerary.days}
            pendingProposal={activeProposal}
            isMobileChips={true}
          />
        )}

        {/* 3-Column Desktop Layout */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start flex-1">
          {/* Column 1: Day Nav + Budget Bar (Left, 3 cols) */}
          <div className="hidden md:flex md:col-span-3 flex-col gap-5 sticky top-36">
            <Card className="p-4 shadow-card">
              {itinerary?.days && (
                <DayNav
                  days={itinerary.days}
                  pendingProposal={activeProposal}
                />
              )}
            </Card>

            {budgetData && (
              <BudgetBar
                budget={budgetData}
                currency={trip?.currency}
                onReduceCost={() => {
                  setActiveTab('budget');
                  setToast({
                    type: 'info',
                    text: 'Review budget and adjust itinerary stops to recover costs.',
                  });
                }}
              />
            )}
          </div>

          {/* Column 2: Center Content (Desktop: 6 or 9 cols depending on agent panel) */}
          <div
            className={`flex-1 ${
              isAgentPanelOpen ? 'md:col-span-6 lg:col-span-6' : 'md:col-span-9 lg:col-span-9'
            } space-y-6`}
          >
            {/* Desktop Tabs Header */}
            <div className="hidden md:flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-1.5 bg-surface-alt p-1 rounded-card border border-border">
                {(['itinerary', 'map', 'budget'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-1.5 rounded-[10px] text-xs font-semibold capitalize transition-all ${
                      activeTab === tab
                        ? 'bg-surface text-text-primary shadow-xs'
                        : 'text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {currentDay && (
                <span className="text-xs text-text-muted font-mono">
                  Day {currentDay.day_index} of {itinerary?.days?.length || 1}
                </span>
              )}
            </div>

            {/* TAB: ITINERARY */}
            {activeTab === 'itinerary' && (
              <div className="space-y-4">
                {/* Generating Skeleton State */}
                {isGenerating ? (
                  <div className="space-y-4">
                    <Card className="p-8 text-center space-y-3 bg-primary/10 border-primary/20">
                      <Loader2 className="h-6 w-6 animate-spin text-primary mx-auto" strokeWidth={1.75} />
                      <h3 className="text-base font-bold text-text-primary">
                        Generating optimal itinerary...
                      </h3>
                      <p className="text-xs text-text-muted max-w-sm mx-auto">
                        Evaluating weather forecasts, operating hours, route travel times, and your budget.
                      </p>
                    </Card>

                    {[1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="h-28 rounded-card bg-surface-alt animate-pulse"
                      />
                    ))}
                  </div>
                ) : currentDay ? (
                  <>
                    <div className="flex items-center justify-between pb-1">
                      <h2 className="text-base font-bold text-text-primary">
                        Day {currentDay.day_index}: {new Date(currentDay.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                      </h2>
                      <span className="text-xs text-text-muted font-medium">
                        {currentDay.items.length} stops planned
                      </span>
                    </div>

                    <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={handleDragEnd}
                    >
                      <SortableContext
                        items={currentDay.items.map((i) => i.stable_key)}
                        strategy={verticalListSortingStrategy}
                      >
                        <div className="space-y-1">
                          {currentDay.items.map((item, index) => {
                            const isAffected = affectedKeys.includes(item.stable_key);
                            const isHighlighted = item.id === highlightedItemId;

                            return (
                              <React.Fragment key={item.id}>
                                {index > 0 && <TravelConnector travel={item.travel} />}
                                <SortableItineraryItem
                                  item={item}
                                  currency={trip?.currency}
                                  isHighlighted={isHighlighted}
                                  isAffected={isAffected}
                                  onToggleLock={(locked: boolean) =>
                                    toggleLockMutation.mutate({ itemId: item.id, isLocked: locked })
                                  }
                                  onDelete={() => deleteItemMutation.mutate(item.id)}
                                />
                              </React.Fragment>
                            );
                          })}
                        </div>
                      </SortableContext>
                    </DndContext>

                    {/* Day Summary Footer */}
                    <DaySummary
                      summary={currentDay.summary}
                      currency={trip?.currency}
                      className="mt-6"
                    />
                  </>
                ) : (
                  <Card className="p-8 text-center text-xs text-text-muted border-dashed">
                    No items found for this day.
                  </Card>
                )}
              </div>
            )}

            {/* TAB: MAP */}
            {activeTab === 'map' && currentDay && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
                    <MapIcon className="h-5 w-5 text-primary" strokeWidth={1.75} />
                    Day {currentDay.day_index} Route Map
                  </h3>
                  <span className="text-xs text-text-muted font-mono">
                    {currentDay.items.length} pin markers
                  </span>
                </div>

                <div className="h-[500px]">
                  <MapView
                    items={currentDay.items}
                    highlightedItemId={highlightedItemId}
                    affectedStableKeys={affectedKeys}
                    onMarkerClick={(item) => {
                      setHighlightedItemId(item.id);
                      setToast({
                        type: 'info',
                        text: `Selected: ${item.title}`,
                      });
                    }}
                    className="h-full"
                  />
                </div>
              </div>
            )}

            {/* TAB: BUDGET */}
            {activeTab === 'budget' && budgetData && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-text-primary flex items-center gap-2">
                    <DollarSign className="h-5 w-5 text-primary" strokeWidth={1.75} />
                    Trip Budget & Expenses
                  </h3>
                  {budgetData.overrun_pct >= 10 && (
                    <Badge variant="accent" className="font-semibold text-xs">
                      Over Budget ({Math.round(budgetData.overrun_pct)}%)
                    </Badge>
                  )}
                </div>

                {/* SVG Donut Chart + Category Breakdown */}
                <Card className="p-6 shadow-card space-y-4">
                  <div className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                    Category Breakdown
                  </div>
                  <BudgetDonutChart budget={budgetData} currency={trip?.currency} />
                </Card>

                {/* Add Expense Form */}
                <ExpenseForm
                  currency={trip?.currency}
                  isSubmitting={addExpenseMutation.isPending}
                  onSubmit={(exp) => addExpenseMutation.mutate(exp)}
                />

                {/* Logged Expense List */}
                <Card className="p-5 space-y-4 shadow-card">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                      Logged Expenses ({expensesList.length})
                    </div>
                    <span className="text-xs font-mono text-text-muted">
                      Total: {formatCurrency(expensesList.reduce((s, e) => s + e.amount_in_trip_currency, 0), trip?.currency)}
                    </span>
                  </div>

                  {expensesList.length === 0 ? (
                    <div className="p-6 text-center text-xs text-text-muted border border-dashed rounded-card">
                      No expenses logged yet. Add one above to track daily spending.
                    </div>
                  ) : (
                    <div className="divide-y divide-border">
                      {expensesList.map((exp) => {
                        const CategoryIcon =
                          CATEGORY_ICONS[exp.category.toLowerCase()] || DollarSign;

                        return (
                          <div
                            key={exp.id}
                            className="py-3 flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center gap-3">
                              <IconCircle size="sm" color="slate">
                                <CategoryIcon className="h-4 w-4" strokeWidth={1.75} />
                              </IconCircle>
                              <div>
                                <div className="font-semibold text-text-primary">
                                  {exp.description || 'Expense'}
                                </div>
                                <div className="text-[11px] text-text-muted capitalize">
                                  {exp.category} • {new Date(exp.spent_at).toLocaleDateString()}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className="font-mono font-bold text-text-primary text-sm">
                                {formatCurrency(exp.amount_in_trip_currency, trip?.currency)}
                              </span>
                              <button
                                type="button"
                                onClick={() => deleteExpenseMutation.mutate(exp.id)}
                                aria-label={`Delete expense ${exp.description || ''}`}
                                className="text-text-muted hover:text-danger p-1.5 rounded-[6px] hover:bg-surface-alt transition-colors"
                              >
                                <Trash2 className="h-4 w-4" strokeWidth={1.75} />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              </div>
            )}

            {/* TAB: AGENT (Mobile tab) */}
            {activeTab === 'agent' && (
              <div className="space-y-4 md:hidden">
                <Card className="p-4 shadow-card">
                  <AgentTimeline events={streamEvents} isRunning={isStreamRunning} />
                </Card>
                <Card className="h-[440px] flex flex-col overflow-hidden shadow-card">
                  <AgentChat
                    tripId={tripId}
                    streamingText={streamingText}
                    onRunStarted={(runId) => setActiveRunId(runId)}
                  />
                </Card>
              </div>
            )}
          </div>

          {/* Column 3: Agent Panel (Desktop Right, collapsible, 3 cols) */}
          {isAgentPanelOpen && (
            <div className="hidden lg:flex lg:col-span-3 flex-col gap-5 sticky top-36">
              <Card className="p-4 shadow-card max-h-[320px] overflow-y-auto">
                <AgentTimeline events={streamEvents} isRunning={isStreamRunning} />
              </Card>

              <Card className="h-[420px] flex flex-col overflow-hidden shadow-card">
                <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-surface-alt">
                  <span className="text-xs font-semibold text-text-primary flex items-center gap-2">
                    <Bot className="h-4 w-4 text-primary" strokeWidth={1.75} /> Assistant Chat
                  </span>
                  <span className="text-[10px] text-text-muted font-mono">HITL replanner</span>
                </div>
                <AgentChat
                  tripId={tripId}
                  streamingText={streamingText}
                  onRunStarted={(runId) => setActiveRunId(runId)}
                />
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Glass Bottom Tab Bar */}
      <div className="md:hidden sticky bottom-0 z-30 bg-surface/85 backdrop-blur-md border-t border-border px-2 py-1.5 flex items-center justify-around shadow-lg">
        {(['itinerary', 'map', 'budget', 'agent'] as const).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-1.5 flex flex-col items-center justify-center gap-1 text-[11px] font-semibold capitalize transition-all rounded-[8px] ${
                isActive
                  ? 'text-primary font-bold bg-primary/10 dark:bg-primary/20'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {tab === 'itinerary' && <Calendar className="h-4 w-4" strokeWidth={1.75} />}
              {tab === 'map' && <MapIcon className="h-4 w-4" strokeWidth={1.75} />}
              {tab === 'budget' && <DollarSign className="h-4 w-4" strokeWidth={1.75} />}
              {tab === 'agent' && <Bot className="h-4 w-4" strokeWidth={1.75} />}
              <span>{tab}</span>
            </button>
          );
        })}
      </div>

      {/* Proposal Review Modal / Sheet */}
      {activeProposal && (
        <ProposalSheet
          isOpen={isProposalSheetOpen}
          onClose={() => setProposalSheetOpen(false)}
          proposal={activeProposal}
          tripId={tripId}
          currency={trip?.currency}
          onOpenStream={(runId) => setActiveRunId(runId)}
        />
      )}
    </div>
  );
}
