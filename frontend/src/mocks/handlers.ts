import {
  Trip,
  TripCreate,
  ItineraryResponse,
  ItineraryVersion,
  ProposalResponse,
  Expense,
  ExpenseCreate,
  BudgetSummary,
  ChatMessage,
  User,
  ProposalDecisionRequest,
  ProposalDecisionResponse,
  AgentEvent,
  ItineraryItem,
  DisruptionType,
  SettingType,
  ExpenseCategory,
} from '@/types/contract';
import {
  SEED_USER,
  SEED_TRIPS,
  SEED_DARJEELING_ITINERARY_V1,
  SEED_JAIPUR_PROPOSAL,
  SEED_EXPENSES,
  SEED_CHAT_MESSAGES,
} from './seed';
import {
  getPlanGenerationEvents,
  getDisruptionReplanEvents,
  getChatEvents,
} from './sse-fixtures';

// In-memory persistent mock state
class MockStore {
  user: User = { ...SEED_USER };
  trips: Trip[] = [...SEED_TRIPS];
  itineraries: Record<string, ItineraryResponse> = {
    'trip-darjeeling-01': JSON.parse(JSON.stringify(SEED_DARJEELING_ITINERARY_V1)),
    'trip-jaipur-02': {
      trip_id: 'trip-jaipur-02',
      version: {
        id: 'ver-jaipur-v1',
        trip_id: 'trip-jaipur-02',
        version_no: 1,
        reason: 'Initial plan',
        created_by: 'agent:planner',
        total_cost: 21500,
        summary: '3-day royal heritage & food tour across the Pink City.',
        created_at: '2026-11-12T14:20:00Z',
      },
      days: [
        {
          day_index: 1,
          date: '2027-01-08',
          summary: { cost: 5200, walking_min: 50, active_min: 450 },
          items: [
            {
              id: 'jp-1',
              stable_key: 'stb-hawa-mahal',
              position: 0,
              title: 'Hawa Mahal Palace of Winds',
              category: 'culture',
              setting: 'outdoor',
              start_time: '09:00',
              end_time: '10:30',
              est_cost: 200,
              lat: 26.9239,
              lng: 75.8267,
              is_locked: false,
              flags: ['outdoor'],
              travel: { mode: 'taxi', minutes: 15, distance_m: 3500 },
            },
            {
              id: 'jp-2',
              stable_key: 'stb-jantar-mantar',
              position: 1,
              title: 'Jantar Mantar Astronomical Observatory',
              category: 'culture',
              setting: 'outdoor',
              start_time: '11:00',
              end_time: '12:30',
              est_cost: 200,
              lat: 26.9248,
              lng: 75.8246,
              is_locked: false,
              flags: ['outdoor'],
              travel: { mode: 'walk', minutes: 8, distance_m: 600 },
            },
            {
              id: 'jp-3',
              stable_key: 'stb-laxmi-misthan',
              position: 2,
              title: 'Laxmi Mishthan Bhandar (LMB) Ghewar & Thali',
              category: 'food',
              setting: 'indoor',
              start_time: '13:00',
              end_time: '14:30',
              est_cost: 1500,
              lat: 26.9213,
              lng: 75.8258,
              is_locked: false,
              flags: [],
              travel: { mode: 'walk', minutes: 10, distance_m: 750 },
            },
          ],
        },
        {
          day_index: 2,
          date: '2027-01-09',
          summary: { cost: 6500, walking_min: 60, active_min: 480 },
          items: [
            {
              id: 'jp-4',
              stable_key: 'stb-amber-fort',
              position: 0,
              title: 'Amer Fort & Sheesh Mahal',
              category: 'culture',
              setting: 'mixed',
              start_time: '09:00',
              end_time: '12:00',
              est_cost: 500,
              lat: 26.9855,
              lng: 75.8513,
              is_locked: false,
              flags: [],
              travel: { mode: 'taxi', minutes: 25, distance_m: 11000 },
            },
            {
              id: 'jp-5',
              stable_key: 'stb-jaigarh-fort',
              position: 1,
              title: 'Jaigarh Fort & Open Cannon Walk',
              category: 'sightseeing',
              setting: 'outdoor',
              start_time: '14:00',
              end_time: '16:00',
              est_cost: 400,
              lat: 26.985,
              lng: 75.8456,
              is_locked: false,
              flags: ['outdoor', 'weather_risk'],
              travel: { mode: 'taxi', minutes: 10, distance_m: 2500 },
            },
            {
              id: 'jp-6',
              stable_key: 'stb-nahargarh-sunset',
              position: 2,
              title: 'Nahargarh Fort Sunset Point',
              category: 'nature',
              setting: 'outdoor',
              start_time: '16:30',
              end_time: '18:00',
              est_cost: 250,
              lat: 26.9372,
              lng: 75.8156,
              is_locked: false,
              flags: ['outdoor', 'weather_risk'],
              travel: { mode: 'taxi', minutes: 20, distance_m: 5500 },
            },
          ],
        },
      ],
    },
  };

  versions: Record<string, ItineraryVersion[]> = {
    'trip-darjeeling-01': [
      {
        id: 'ver-darjeeling-v1',
        trip_id: 'trip-darjeeling-01',
        version_no: 1,
        reason: 'Initial plan',
        created_by: 'agent:planner',
        total_cost: 14200,
        summary: '3-day balanced itinerary covering sunrise, heritage railway, and local tea estates.',
        created_at: '2026-11-10T08:35:00Z',
      },
    ],
    'trip-jaipur-02': [
      {
        id: 'ver-jaipur-v1',
        trip_id: 'trip-jaipur-02',
        version_no: 1,
        reason: 'Initial plan',
        created_by: 'agent:planner',
        total_cost: 21500,
        summary: '3-day royal heritage & food tour across the Pink City.',
        created_at: '2026-11-12T14:20:00Z',
      },
    ],
  };

  proposals: Record<string, ProposalResponse[]> = {
    'trip-darjeeling-01': [],
    'trip-jaipur-02': [JSON.parse(JSON.stringify(SEED_JAIPUR_PROPOSAL))],
  };

  expenses: Record<string, Expense[]> = JSON.parse(JSON.stringify(SEED_EXPENSES));
  chat: Record<string, ChatMessage[]> = JSON.parse(JSON.stringify(SEED_CHAT_MESSAGES));

  runs: Record<
    string,
    {
      trip_id: string;
      type: string;
      events: AgentEvent[];
      status: string;
    }
  > = {};

  // Track run listeners for SSE simulation
  private runListeners: Record<string, Set<(event: AgentEvent) => void>> = {};
  private runErrorListeners: Record<string, Set<(err: unknown) => void>> = {};
  public activeConnectionsCount: number = 0;

  subscribeRun(
    runId: string,
    listener: (event: AgentEvent) => void,
    lastEventId?: string,
    onError?: (err: unknown) => void
  ) {
    this.activeConnectionsCount += 1;
    if (!this.runListeners[runId]) {
      this.runListeners[runId] = new Set();
    }
    this.runListeners[runId].add(listener);

    if (onError) {
      if (!this.runErrorListeners[runId]) {
        this.runErrorListeners[runId] = new Set();
      }
      this.runErrorListeners[runId].add(onError);
    }

    let interval: NodeJS.Timeout | null = null;
    const run = this.runs[runId];
    if (run) {
      const minSeq = lastEventId ? parseInt(lastEventId, 10) : 0;
      const eventsToSend = run.events.filter((ev) => (ev.seq ?? 0) > minSeq);
      let index = 0;
      interval = setInterval(() => {
        if (index < eventsToSend.length) {
          const ev = eventsToSend[index];
          listener(ev);
          index++;
        } else {
          if (interval) clearInterval(interval);
        }
      }, 50);
    }

    return () => {
      this.activeConnectionsCount = Math.max(0, this.activeConnectionsCount - 1);
      if (interval) clearInterval(interval);
      this.runListeners[runId]?.delete(listener);
      if (onError) {
        this.runErrorListeners[runId]?.delete(onError);
      }
    };
  }

  emitRunEvent(runId: string, event: AgentEvent) {
    this.runListeners[runId]?.forEach((fn) => fn(event));
  }

  emitRunError(runId: string, error: unknown) {
    this.runErrorListeners[runId]?.forEach((fn) => fn(error));
  }

  // API Methods
  getTrips(): Trip[] {
    return this.trips.map((t) => {
      const pendingProps = this.proposals[t.id]?.filter((p) => p.status === 'pending') || [];
      return {
        ...t,
        has_pending_proposal: pendingProps.length > 0,
        status: pendingProps.length > 0 ? 'needs_attention' : t.status,
      };
    });
  }

  getTrip(id: string): Trip | null {
    const trip = this.trips.find((t) => t.id === id);
    if (!trip) return null;
    const pendingProps = this.proposals[id]?.filter((p) => p.status === 'pending') || [];
    return {
      ...trip,
      has_pending_proposal: pendingProps.length > 0,
      status: pendingProps.length > 0 ? 'needs_attention' : trip.status,
    };
  }

  createTrip(payload: TripCreate): Trip {
    const id = `trip-${Date.now()}`;
    const newTrip: Trip = {
      id,
      user_id: this.user.id,
      title: payload.title || `${payload.destination} Trip`,
      destination: payload.destination,
      dest_lat: 27.036,
      dest_lng: 88.2627,
      start_date: payload.start_date,
      end_date: payload.end_date,
      group_size: payload.group_size,
      budget_total: payload.budget_total,
      budget_per_day_cap: payload.budget_per_day_cap,
      currency: payload.currency,
      pace: payload.pace,
      vibe_tags: payload.vibe_tags,
      notes: payload.notes,
      status: 'draft',
      current_version_id: null,
      has_pending_proposal: false,
      last_checked_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      image_url: 'https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=800&q=80',
    };
    this.trips.unshift(newTrip);
    this.itineraries[id] = {
      trip_id: id,
      version: {
        id: `ver-${id}-1`,
        trip_id: id,
        version_no: 1,
        reason: 'Initial plan',
        created_by: 'agent:planner',
        total_cost: payload.budget_total * 0.8,
        summary: `Tailored itinerary for ${payload.destination}`,
        created_at: new Date().toISOString(),
      },
      days: [],
    };
    this.versions[id] = [this.itineraries[id].version];
    this.proposals[id] = [];
    this.expenses[id] = [];
    this.chat[id] = [];
    return newTrip;
  }

  updateTrip(id: string, updates: Partial<Trip>): Trip | null {
    const index = this.trips.findIndex((t) => t.id === id);
    if (index === -1) return null;
    this.trips[index] = { ...this.trips[index], ...updates, updated_at: new Date().toISOString() };
    return this.trips[index];
  }

  deleteTrip(id: string): boolean {
    this.trips = this.trips.filter((t) => t.id !== id);
    delete this.itineraries[id];
    delete this.versions[id];
    delete this.proposals[id];
    delete this.expenses[id];
    delete this.chat[id];
    return true;
  }

  getItinerary(tripId: string): ItineraryResponse | null {
    return this.itineraries[tripId] || null;
  }

  getVersions(tripId: string): ItineraryVersion[] {
    return this.versions[tripId] || [];
  }

  restoreVersion(tripId: string, versionId: string): ItineraryResponse | null {
    const versionList = this.versions[tripId] || [];
    const target = versionList.find((v) => v.id === versionId);
    if (!target) return null;

    const newVersionNo = versionList.length + 1;
    const newVersionId = `ver-${tripId}-v${newVersionNo}`;
    const newVersion: ItineraryVersion = {
      id: newVersionId,
      trip_id: tripId,
      version_no: newVersionNo,
      parent_version_id: versionId,
      reason: `Restored to version ${target.version_no}`,
      created_by: 'user',
      total_cost: target.total_cost,
      summary: target.summary,
      created_at: new Date().toISOString(),
    };

    versionList.push(newVersion);
    this.versions[tripId] = versionList;

    if (this.itineraries[tripId]) {
      this.itineraries[tripId].version = newVersion;
    }

    const trip = this.trips.find((t) => t.id === tripId);
    if (trip) {
      trip.current_version_id = newVersionId;
    }

    return this.itineraries[tripId];
  }

  updateItem(itemId: string, patch: Partial<ItineraryItem>): ItineraryItem | null {
    for (const tripId in this.itineraries) {
      const itin = this.itineraries[tripId];
      for (const day of itin.days) {
        const item = day.items.find((i) => i.id === itemId);
        if (item) {
          Object.assign(item, patch);
          return item;
        }
      }
    }
    return null;
  }

  deleteItem(itemId: string): boolean {
    for (const tripId in this.itineraries) {
      const itin = this.itineraries[tripId];
      for (const day of itin.days) {
        const idx = day.items.findIndex((i) => i.id === itemId);
        if (idx !== -1) {
          day.items.splice(idx, 1);
          return true;
        }
      }
    }
    return false;
  }

  reorderItems(tripId: string, dayIndex: number, orderedKeys: string[]): boolean {
    const itin = this.itineraries[tripId];
    if (!itin) return false;
    const day = itin.days.find((d) => d.day_index === dayIndex);
    if (!day) return false;

    const keyMap = new Map(day.items.map((i) => [i.stable_key, i]));
    const newItems: ItineraryItem[] = [];
    orderedKeys.forEach((key, pos) => {
      const item = keyMap.get(key);
      if (item) {
        item.position = pos;
        newItems.push(item);
      }
    });

    day.items = newItems;
    return true;
  }

  startGenerate(tripId: string): string {
    const runId = `run-plan-${Date.now()}`;
    const versionId = `ver-${tripId}-v1`;
    const events = getPlanGenerationEvents(tripId, versionId);

    const trip = this.trips.find((t) => t.id === tripId);
    if (trip) {
      trip.status = 'planned';
      trip.current_version_id = versionId;
    }
    this.itineraries[tripId] = {
      trip_id: tripId,
      version: {
        id: versionId,
        trip_id: tripId,
        version_no: 1,
        reason: 'Initial plan',
        created_by: 'agent:planner',
        total_cost: trip ? trip.budget_total * 0.75 : 12000,
        summary: `Curated itinerary for ${trip?.destination || 'your trip'}`,
        created_at: new Date().toISOString(),
      },
      days: JSON.parse(JSON.stringify(SEED_DARJEELING_ITINERARY_V1.days)),
    };

    this.runs[runId] = {
      trip_id: tripId,
      type: 'plan',
      events,
      status: 'running',
    };

    return runId;
  }

  startCheck(tripId: string): string {
    return this.simulateDisruption(tripId, 'weather', 2);
  }

  simulateDisruption(
    tripId: string,
    type: 'weather' | 'closure' | 'delay' | 'budget_overrun',
    dayIndex: number = 2
  ): string {
    const runId = `run-sim-${type}-${Date.now()}`;
    const proposalId = `prop-${tripId}-${type}-${Date.now()}`;

    const events = getDisruptionReplanEvents(type, proposalId);
    this.runs[runId] = {
      trip_id: tripId,
      type: 'replan',
      events,
      status: 'running',
    };

    // Prepare the proposal in store
    const proposal: ProposalResponse = {
      id: proposalId,
      trip_id: tripId,
      run_id: runId,
      base_version_id: this.itineraries[tripId]?.version?.id || 'ver-1',
      status: 'pending',
      reason:
        type === 'weather'
          ? `Rain expected Day ${dayIndex}, 2-6pm (80%). 2 outdoor stops affected.`
          : type === 'closure'
          ? `Attraction closed on Day ${dayIndex} for maintenance.`
          : type === 'delay'
          ? `Train delayed 2 hours on Day ${dayIndex}. Morning schedule shifted.`
          : `Budget overrun: actual spend exceeds planned by 14%.`,
      explanation:
        type === 'weather'
          ? 'Swapped 2 outdoor stops for indoor cultural experiences within 1.2 km, keeping total cost under budget.'
          : type === 'closure'
          ? 'Substituted closed attraction with nearby Tibetan arts gallery.'
          : type === 'delay'
          ? 'Condensed morning stops and moved sunrise trek forward to preserve key sightseeing.'
          : 'Replaced high-cost activity with a scenic nature walk to keep overall trip within budget.',
      disruptions: [
        {
          id: `disrupt-${Date.now()}`,
          trip_id: tripId,
          type: type as DisruptionType,
          severity: 'high',
          day_index: dayIndex,
          summary:
            type === 'weather'
              ? `Rain expected Day ${dayIndex}, 2-6pm (80%). 2 outdoor stops affected.`
              : `Disruption signal: ${type}`,
          source: type === 'weather' ? 'Open-Meteo Weather API' : 'Real-time monitor',
        },
      ],
      cost_delta: type === 'budget_overrun' ? -1400 : -150,
      time_delta_min: 10,
      items_changed: 2,
      diff: [
        {
          op: 'replace',
          day: dayIndex,
          stable_key: 'stb-happy-valley-tea',
          before: {
            title: 'Happy Valley Tea Estate Tour',
            start: '14:00',
            end: '16:00',
            cost: 500,
            setting: 'outdoor',
            category: 'sightseeing',
          },
          after: {
            title: 'Tibetan Refugee Self-Help Centre (Indoor Workshop)',
            place_id: 'plc-tibetan-crafts',
            start: '14:00',
            end: '16:00',
            cost: 200,
            setting: 'indoor',
            category: 'culture',
          },
          why: 'Outdoor tea garden visit during 80% heavy rain downpour',
        },
        {
          op: 'replace',
          day: dayIndex,
          stable_key: 'stb-ropeway-ride',
          before: {
            title: 'Rangeet Valley Passenger Ropeway',
            start: '16:30',
            end: '17:45',
            cost: 700,
            setting: 'outdoor',
            category: 'adventure',
          },
          after: {
            title: 'Ava Art Gallery & Botanical Embroidery Display',
            place_id: 'plc-ava-gallery',
            start: '16:30',
            end: '17:45',
            cost: 150,
            setting: 'indoor',
            category: 'culture',
          },
          why: 'Cable car halted during rainstorm; indoor heritage art gallery chosen',
        },
      ],
      created_at: new Date().toISOString(),
    };

    // Filter out any items that are locked in the user's itinerary: locked items NEVER appear in diff
    const itin = this.itineraries[tripId];
    const day = itin?.days.find((d) => d.day_index === dayIndex);
    const lockedKeys = new Set(day?.items.filter((i) => i.is_locked).map((i) => i.stable_key) || []);
    proposal.diff = proposal.diff.filter((d) => !lockedKeys.has(d.stable_key));
    proposal.items_changed = proposal.diff.length;

    // Supersede any existing pending proposals for this trip
    const existingPending = (this.proposals[tripId] || []).filter((p) => p.status === 'pending');
    existingPending.forEach((p) => {
      p.status = 'superseded';
    });

    if (!this.proposals[tripId]) {
      this.proposals[tripId] = [];
    }
    this.proposals[tripId].unshift(proposal);

    const trip = this.trips.find((t) => t.id === tripId);
    if (trip) {
      trip.has_pending_proposal = true;
      trip.status = 'needs_attention';
    }

    return runId;
  }

  getProposals(tripId: string, status?: string): ProposalResponse[] {
    const list = this.proposals[tripId] || [];
    if (status) {
      return list.filter((p) => p.status === status);
    }
    return list;
  }

  getProposal(id: string): ProposalResponse | null {
    for (const tripId in this.proposals) {
      const found = this.proposals[tripId].find((p) => p.id === id);
      if (found) return found;
    }
    return null;
  }

  decideProposal(
    proposalId: string,
    req: ProposalDecisionRequest
  ): ProposalDecisionResponse {
    let target: ProposalResponse | null = null;
    let targetTripId: string = '';

    for (const tripId in this.proposals) {
      const found = this.proposals[tripId].find((p) => p.id === proposalId);
      if (found) {
        target = found;
        targetTripId = tripId;
        break;
      }
    }

    if (!target) {
      throw new Error('Proposal not found');
    }

    if (target.status !== 'pending') {
      throw new Error('Proposal already decided or superseded');
    }

    if (req.decision === 'approve') {
      target.status = 'approved';
      const trip = this.trips.find((t) => t.id === targetTripId);
      const curVersionList = this.versions[targetTripId] || [];
      const newVersionNo = curVersionList.length + 1;
      const newVersionId = `ver-${targetTripId}-v${newVersionNo}`;

      const newVersion: ItineraryVersion = {
        id: newVersionId,
        trip_id: targetTripId,
        version_no: newVersionNo,
        parent_version_id: target.base_version_id,
        reason: target.reason,
        created_by: 'agent:replanner',
        total_cost:
          (this.itineraries[targetTripId]?.version?.total_cost || 14000) + target.cost_delta,
        summary: target.explanation,
        created_at: new Date().toISOString(),
      };

      curVersionList.push(newVersion);
      this.versions[targetTripId] = curVersionList;

      // Apply the diff to the itinerary items
      const itin = this.itineraries[targetTripId];
      if (itin) {
        itin.version = newVersion;
        target.diff.forEach((diffItem) => {
          const day = itin.days.find((d) => d.day_index === diffItem.day);
          if (day && diffItem.after) {
            const item = day.items.find((i) => i.stable_key === diffItem.stable_key);
            if (item) {
              item.title = diffItem.after.title;
              item.start_time = diffItem.after.start;
              item.end_time = diffItem.after.end;
              item.est_cost = diffItem.after.cost;
              item.setting = (diffItem.after.setting as SettingType) || 'indoor';
              item.flags = item.flags.filter((f) => f !== 'weather_risk');
            }
          }
        });
      }

      if (trip) {
        trip.has_pending_proposal = false;
        trip.status = 'planned';
        trip.current_version_id = newVersionId;
      }

      return { status: 'approved', version_id: newVersionId };
    } else if (req.decision === 'reject') {
      target.status = 'rejected';
      const trip = this.trips.find((t) => t.id === targetTripId);
      if (trip) {
        trip.has_pending_proposal = false;
        trip.status = 'planned';
      }
      return { status: 'rejected' };
    } else {
      // Alternatives
      target.status = 'superseded';
      const altRunId = `run-alt-${Date.now()}`;
      const altPropId = `prop-alt-${Date.now()}`;
      const events = getDisruptionReplanEvents('weather', altPropId);

      this.runs[altRunId] = {
        trip_id: targetTripId,
        type: 'replan',
        events,
        status: 'running',
      };

      return { status: 'superseded', run_id: altRunId };
    }
  }

  sendChat(tripId: string, message: string): { run_id: string; message_id: string } {
    if (!this.chat[tripId]) {
      this.chat[tripId] = [];
    }

    const userMsgId = `msg-${Date.now()}`;
    this.chat[tripId].push({
      id: userMsgId,
      trip_id: tripId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    });

    const runId = `run-chat-${Date.now()}`;
    const events = getChatEvents();

    this.runs[runId] = {
      trip_id: tripId,
      type: 'chat',
      events,
      status: 'running',
    };

    setTimeout(() => {
      this.chat[tripId]?.push({
        id: `msg-rep-${Date.now()}`,
        trip_id: tripId,
        role: 'assistant',
        content: `I've adjusted the plan based on "${message}". You can review the proposed changes above.`,
        created_at: new Date().toISOString(),
      });
    }, 1800);

    return { run_id: runId, message_id: userMsgId };
  }

  getChatHistory(tripId: string): ChatMessage[] {
    return this.chat[tripId] || [];
  }

  getExpenses(tripId: string): Expense[] {
    return this.expenses[tripId] || [];
  }

  addExpense(tripId: string, payload: ExpenseCreate): Expense {
    const expense: Expense = {
      id: `exp-${Date.now()}`,
      trip_id: tripId,
      user_id: this.user.id,
      item_stable_key: payload.item_stable_key,
      category: payload.category,
      amount: payload.amount,
      currency: payload.currency || 'INR',
      amount_in_trip_currency: payload.amount,
      description: payload.description,
      spent_at: payload.spent_at || new Date().toISOString(),
      created_at: new Date().toISOString(),
    };

    if (!this.expenses[tripId]) {
      this.expenses[tripId] = [];
    }
    this.expenses[tripId].unshift(expense);
    return expense;
  }

  deleteExpense(id: string): boolean {
    for (const tripId in this.expenses) {
      const idx = this.expenses[tripId].findIndex((e) => e.id === id);
      if (idx !== -1) {
        this.expenses[tripId].splice(idx, 1);
        return true;
      }
    }
    return false;
  }

  getBudget(tripId: string): BudgetSummary {
    const trip = this.trips.find((t) => t.id === tripId);
    const plannedTotal = trip ? trip.budget_total : 15000;
    const expenses = this.expenses[tripId] || [];
    const actualTotal = expenses.reduce((sum, e) => sum + e.amount_in_trip_currency, 0);

    const categories: Record<string, { planned: number; actual: number }> = {
      stay: { planned: plannedTotal * 0.4, actual: 0 },
      food: { planned: plannedTotal * 0.25, actual: 0 },
      transport: { planned: plannedTotal * 0.2, actual: 0 },
      activities: { planned: plannedTotal * 0.15, actual: 0 },
    };

    expenses.forEach((e) => {
      if (categories[e.category]) {
        categories[e.category].actual += e.amount_in_trip_currency;
      }
    });

    const overrunPct =
      actualTotal > plannedTotal ? ((actualTotal - plannedTotal) / plannedTotal) * 100 : 0;

    return {
      planned_total: plannedTotal,
      actual_total: actualTotal,
      remaining: Math.max(0, plannedTotal - actualTotal),
      by_category: Object.entries(categories).map(([category, val]) => ({
        category: category as ExpenseCategory,
        planned: val.planned,
        actual: val.actual,
      })),
      overrun_pct: overrunPct,
    };
  }
}

export const mockStore = new MockStore();
