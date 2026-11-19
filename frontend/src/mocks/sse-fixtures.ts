import { AgentEvent } from '@/types/contract';

export function getPlanGenerationEvents(tripId: string, versionId: string): AgentEvent[] {
  return [
    {
      seq: 1,
      type: 'step',
      node: 'intake',
      message: 'Analyzing travel dates, group size, and vibe preferences',
      status: 'running',
    },
    {
      seq: 2,
      type: 'step',
      node: 'intake',
      message: 'Trip preferences normalized into TripSpec',
      status: 'done',
    },
    {
      seq: 3,
      type: 'tool_call',
      node: 'researcher',
      message: 'Querying local attractions, operating hours, and geo coordinates',
      status: 'running',
      payload: { tool: 'search_places', args: { city: 'Darjeeling', vibe: ['nature', 'food'] } },
    },
    {
      seq: 4,
      type: 'tool_result',
      node: 'researcher',
      message: 'Retrieved 18 candidate places with verified opening hours',
      status: 'done',
      payload: { tool: 'search_places', ok: true, count: 18 },
    },
    {
      seq: 5,
      type: 'tool_call',
      node: 'researcher',
      message: 'Fetching 7-day weather forecast',
      status: 'running',
      payload: { tool: 'get_weather_forecast', args: { lat: 27.036, lng: 88.262 } },
    },
    {
      seq: 6,
      type: 'tool_result',
      node: 'researcher',
      message: 'Weather forecast clear, temperature 12-16C',
      status: 'done',
      payload: { tool: 'get_weather_forecast', ok: true, summary: 'Clear skies' },
    },
    {
      seq: 7,
      type: 'step',
      node: 'planner',
      message: 'Structuring optimized day-by-day itinerary sequence',
      status: 'running',
    },
    {
      seq: 8,
      type: 'draft',
      node: 'planner',
      message: 'Initial day drafts prepared',
      status: 'running',
      payload: { days_ready: [1, 2, 3] },
    },
    {
      seq: 9,
      type: 'step',
      node: 'validator',
      message: 'Running deterministic checks on opening hours, travel gaps, and budget limits',
      status: 'running',
    },
    {
      seq: 10,
      type: 'step',
      node: 'validator',
      message: 'All constraints verified: 0 overlaps, total cost within budget',
      status: 'done',
    },
    {
      seq: 11,
      type: 'step',
      node: 'finalize',
      message: 'Saving itinerary v1 and setting up signal monitors',
      status: 'done',
    },
    {
      seq: 12,
      type: 'done',
      status: 'done',
      message: 'Itinerary successfully generated and ready.',
      payload: { status: 'completed', version_id: versionId, trip_id: tripId },
    },
  ];
}

export function getDisruptionReplanEvents(
  type: 'weather' | 'closure' | 'delay' | 'budget_overrun',
  proposalId: string
): AgentEvent[] {
  switch (type) {
    case 'weather':
      return [
        {
          seq: 1,
          type: 'step',
          node: 'collect_signals',
          message: 'Checking Open-Meteo live atmospheric telemetry',
          status: 'running',
        },
        {
          seq: 2,
          type: 'tool_call',
          node: 'collect_signals',
          message: 'Fetching hourly precipitation probability for Day 2',
          status: 'running',
          payload: { tool: 'open_meteo_hourly', args: { day: 2 } },
        },
        {
          seq: 3,
          type: 'tool_result',
          node: 'collect_signals',
          message: '80% heavy rain detected Day 2 between 14:00 - 18:00',
          status: 'done',
          payload: { precip_prob: 0.8, window: '14:00-18:00' },
        },
        {
          seq: 4,
          type: 'disruption',
          node: 'impact_analyzer',
          message: 'Disruption flagged: 2 outdoor stops coincide with rain window',
          status: 'done',
          payload: {
            type: 'weather',
            severity: 'high',
            summary: 'Rain expected Day 2, 2-6pm (80%). 2 outdoor stops affected.',
          },
        },
        {
          seq: 5,
          type: 'step',
          node: 'replanner',
          message: 'Searching indoor alternatives nearby keeping budget intact',
          status: 'running',
        },
        {
          seq: 6,
          type: 'step',
          node: 'validator',
          message: 'Verifying indoor substitutions against opening hours and travel buffers',
          status: 'done',
        },
        {
          seq: 7,
          type: 'proposal',
          node: 'build_proposal',
          message: 'Replan proposal formulated for user approval',
          status: 'done',
          payload: { proposal_id: proposalId },
        },
        {
          seq: 8,
          type: 'done',
          status: 'done',
          message: 'Run paused awaiting human decision',
          payload: { status: 'awaiting_user', proposal_id: proposalId },
        },
      ];

    case 'closure':
      return [
        {
          seq: 1,
          type: 'step',
          node: 'collect_signals',
          message: 'Re-checking operating hours against official holiday & maintenance feeds',
          status: 'running',
        },
        {
          seq: 2,
          type: 'disruption',
          node: 'impact_analyzer',
          message: 'Disruption flagged: Ropeway closed for scheduled safety inspection',
          status: 'done',
          payload: {
            type: 'closure',
            severity: 'medium',
            summary: 'Rangeet Ropeway closed for maintenance on Day 2.',
          },
        },
        {
          seq: 3,
          type: 'step',
          node: 'replanner',
          message: 'Replacing closed item with Tibetan Craft Center',
          status: 'running',
        },
        {
          seq: 4,
          type: 'proposal',
          node: 'build_proposal',
          message: 'Replan proposal created',
          status: 'done',
          payload: { proposal_id: proposalId },
        },
        {
          seq: 5,
          type: 'done',
          status: 'done',
          message: 'Awaiting user decision',
          payload: { status: 'awaiting_user', proposal_id: proposalId },
        },
      ];

    case 'delay':
      return [
        {
          seq: 1,
          type: 'step',
          node: 'collect_signals',
          message: 'Checking transit status and railway timetable',
          status: 'running',
        },
        {
          seq: 2,
          type: 'disruption',
          node: 'impact_analyzer',
          message: 'Disruption flagged: Inbound train delayed by 120 minutes',
          status: 'done',
          payload: {
            type: 'delay',
            severity: 'high',
            summary: 'Toy Train delayed 2 hours. Morning schedule shifted.',
          },
        },
        {
          seq: 3,
          type: 'step',
          node: 'replanner',
          message: 'Compressing morning schedule and shifting afternoon stops',
          status: 'running',
        },
        {
          seq: 4,
          type: 'proposal',
          node: 'build_proposal',
          message: 'Replan proposal created',
          status: 'done',
          payload: { proposal_id: proposalId },
        },
        {
          seq: 5,
          type: 'done',
          status: 'done',
          message: 'Awaiting user decision',
          payload: { status: 'awaiting_user', proposal_id: proposalId },
        },
      ];

    case 'budget_overrun':
      return [
        {
          seq: 1,
          type: 'step',
          node: 'collect_signals',
          message: 'Aggregating logged expenses against planned daily allocations',
          status: 'running',
        },
        {
          seq: 2,
          type: 'disruption',
          node: 'impact_analyzer',
          message: 'Budget overrun: Actual spend exceeds planned allocation by 14%',
          status: 'done',
          payload: {
            type: 'budget_overrun',
            severity: 'medium',
            summary: 'Expenses are 14% over budget. Recommending free/low-cost activities.',
          },
        },
        {
          seq: 3,
          type: 'step',
          node: 'replanner',
          message: 'Swapping premium dining and activities for scenic self-guided heritage spots',
          status: 'running',
        },
        {
          seq: 4,
          type: 'proposal',
          node: 'build_proposal',
          message: 'Replan proposal created to recover Rs 1,400',
          status: 'done',
          payload: { proposal_id: proposalId },
        },
        {
          seq: 5,
          type: 'done',
          status: 'done',
          message: 'Awaiting user decision',
          payload: { status: 'awaiting_user', proposal_id: proposalId },
        },
      ];
  }
}

export function getChatEvents(proposalId?: string): AgentEvent[] {
  return [
    {
      seq: 1,
      type: 'token',
      payload: { text: "I understand! Let me look into adjusting Day 2 to be more relaxed. " },
    },
    {
      seq: 2,
      type: 'token',
      payload: { text: "I'll remove the early sunrise trek and allocate extra time for tea tasting and leisure strolls. " },
    },
    {
      seq: 3,
      type: 'step',
      node: 'replanner',
      message: 'Drafting relaxed schedule proposal',
      status: 'done',
    },
    {
      seq: 4,
      type: 'proposal',
      node: 'build_proposal',
      message: 'Proposal prepared based on your request',
      status: 'done',
      payload: { proposal_id: proposalId || 'prop-chat-relaxed-01' },
    },
    {
      seq: 5,
      type: 'done',
      status: 'done',
      message: 'Completed',
      payload: { status: 'completed' },
    },
  ];
}
