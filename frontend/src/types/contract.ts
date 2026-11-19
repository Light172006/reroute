// Hand-written types from 05_API_AND_AGENT_CONTRACT.md and 04_schema.sql

export type TripStatus =
  | 'draft'
  | 'generating'
  | 'planned'
  | 'needs_attention'
  | 'active'
  | 'done'
  | 'completed'
  | 'archived';

export type PaceType = 'relaxed' | 'balanced' | 'packed';

export type ItemCategory =
  | 'sightseeing'
  | 'food'
  | 'culture'
  | 'nature'
  | 'nightlife'
  | 'shopping'
  | 'adventure'
  | 'transport'
  | 'stay'
  | 'other';

export type SettingType = 'indoor' | 'outdoor' | 'mixed';

export type TransportMode =
  | 'walk'
  | 'taxi'
  | 'bus'
  | 'train'
  | 'metro'
  | 'bike'
  | 'car';

export type DisruptionType =
  | 'weather'
  | 'closure'
  | 'hours_conflict'
  | 'delay'
  | 'budget_overrun'
  | 'user_request';

export type SeverityType = 'low' | 'medium' | 'high';

export type ProposalStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'expired'
  | 'superseded';

export type ExpenseCategory =
  | 'stay'
  | 'food'
  | 'transport'
  | 'activities'
  | 'shopping'
  | 'other';

export interface User {
  id: string;
  email: string;
  display_name: string;
  home_currency: string;
  units: 'metric' | 'imperial';
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface TripCreate {
  title: string;
  destination: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
  group_size: number;
  budget_total: number;
  budget_per_day_cap?: number | null;
  currency: string;
  pace: PaceType;
  vibe_tags: string[];
  notes?: string | null;
}

export interface Trip {
  id: string;
  user_id: string;
  title: string;
  destination: string;
  dest_lat?: number | null;
  dest_lng?: number | null;
  start_date: string;
  end_date: string;
  group_size: number;
  budget_total: number;
  budget_per_day_cap?: number | null;
  currency: string;
  pace: PaceType;
  vibe_tags: string[];
  notes?: string | null;
  status: TripStatus;
  current_version_id?: string | null;
  has_pending_proposal?: boolean;
  last_checked_at?: string | null;
  created_at: string;
  updated_at: string;
  image_url?: string;
}

export interface TravelInfo {
  mode: TransportMode;
  minutes: number;
  distance_m?: number;
}

export interface ItineraryItem {
  id: string;
  stable_key: string;
  position: number;
  title: string;
  category: ItemCategory;
  setting: SettingType;
  start_time: string; // "HH:MM"
  end_time: string;   // "HH:MM"
  est_cost: number;
  lat?: number | null;
  lng?: number | null;
  is_locked: boolean;
  flags: string[];
  travel?: TravelInfo | null;
  place_id?: string | null;
  notes?: string | null;
}

export interface DaySummaryData {
  cost: number;
  walking_min: number;
  active_min: number;
}

export interface ItineraryDay {
  day_index: number;
  date: string;
  summary: DaySummaryData;
  items: ItineraryItem[];
}

export interface ItineraryVersion {
  id: string;
  trip_id: string;
  version_no: number;
  parent_version_id?: string | null;
  reason: string;
  created_by: string; // 'agent:planner' | 'agent:replanner' | 'user'
  total_cost: number;
  summary?: string | null;
  created_at: string;
}

export interface ItineraryResponse {
  trip_id: string;
  version: ItineraryVersion;
  days: ItineraryDay[];
}

export interface DisruptionEvent {
  id: string;
  trip_id?: string;
  type: DisruptionType;
  severity: SeverityType;
  day_index?: number | null;
  window_start?: string | null;
  window_end?: string | null;
  affected_stable_keys?: string[];
  summary: string;
  source: string; // e.g. 'open-meteo'
  data?: Record<string, unknown>;
}

export interface DiffItemData {
  title: string;
  place_id?: string;
  start: string;
  end: string;
  cost: number;
  setting?: string;
  category?: string;
  is_locked?: boolean;
}

export interface ProposalDiffItem {
  op: 'replace' | 'remove' | 'add' | 'move';
  day: number;
  stable_key: string;
  before?: DiffItemData | null;
  after?: DiffItemData | null;
  why?: string;
}

export interface ProposalResponse {
  id: string;
  trip_id: string;
  run_id: string;
  base_version_id: string;
  status: ProposalStatus;
  reason: string;
  explanation: string;
  disruptions: DisruptionEvent[];
  cost_delta: number;
  time_delta_min: number;
  items_changed: number;
  diff: ProposalDiffItem[];
  created_at: string;
  resulting_version_id?: string | null;
}

export interface Expense {
  id: string;
  trip_id: string;
  user_id: string;
  item_stable_key?: string | null;
  category: ExpenseCategory;
  amount: number;
  currency: string;
  amount_in_trip_currency: number;
  description?: string | null;
  spent_at: string;
  created_at: string;
}

export interface ExpenseCreate {
  category: ExpenseCategory;
  amount: number;
  currency?: string;
  description?: string;
  spent_at?: string;
  item_stable_key?: string;
}

export interface CategoryBudget {
  category: ExpenseCategory;
  planned: number;
  actual: number;
}

export interface BudgetSummary {
  planned_total: number;
  actual_total: number;
  remaining: number;
  by_category: CategoryBudget[];
  overrun_pct: number;
}

export interface ChatMessage {
  id: string;
  trip_id: string;
  run_id?: string | null;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type AgentEventType =
  | 'step'
  | 'tool_call'
  | 'tool_result'
  | 'llm_call'
  | 'draft'
  | 'disruption'
  | 'proposal'
  | 'token'
  | 'error'
  | 'done';

export interface AgentEvent {
  seq?: number;
  type: AgentEventType;
  node?: string | null;
  message?: string | null;
  status?: 'running' | 'done' | 'failed' | null;
  payload?: Record<string, unknown>;
  timestamp?: string;
}

export interface AgentRunResponse {
  run_id: string;
  message_id?: string;
}

export interface SimulateRequest {
  trip_id: string;
  type: 'weather' | 'closure' | 'delay' | 'budget_overrun';
  day_index: number;
  params?: Record<string, unknown>;
}

export interface ProposalDecisionRequest {
  decision: 'approve' | 'reject' | 'alternatives';
  note?: string;
}

export interface ProposalDecisionResponse {
  status: 'approved' | 'rejected' | 'superseded';
  version_id?: string;
  run_id?: string;
}
