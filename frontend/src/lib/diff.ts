import { ItineraryDay, ProposalDiffItem, ItineraryItem } from '@/types/contract';

export interface DiffRow {
  key: string;
  op: 'replace' | 'remove' | 'add' | 'move' | 'unchanged';
  day: number;
  before?: {
    title: string;
    start: string;
    end: string;
    cost: number;
    is_locked?: boolean;
    flags?: string[];
  } | null;
  after?: {
    title: string;
    start: string;
    end: string;
    cost: number;
    is_locked?: boolean;
    flags?: string[];
  } | null;
  why?: string;
  isLocked?: boolean;
}

export function computeVersionDiff(daysV1: ItineraryDay[], daysV2: ItineraryDay[]): DiffRow[] {
  const rows: DiffRow[] = [];
  const mapV1 = new Map<string, { item: ItineraryItem; day: number }>();
  const mapV2 = new Map<string, { item: ItineraryItem; day: number }>();

  daysV1.forEach((day) => {
    day.items.forEach((item) => {
      mapV1.set(item.stable_key, { item, day: day.day_index });
    });
  });

  daysV2.forEach((day) => {
    day.items.forEach((item) => {
      mapV2.set(item.stable_key, { item, day: day.day_index });
    });
  });

  // Check items in V1
  mapV1.forEach(({ item: i1, day: d1 }, key) => {
    const v2Entry = mapV2.get(key);
    if (!v2Entry) {
      rows.push({
        key,
        op: 'remove',
        day: d1,
        before: {
          title: i1.title,
          start: i1.start_time,
          end: i1.end_time,
          cost: i1.est_cost,
          is_locked: i1.is_locked,
          flags: i1.flags,
        },
        why: 'Removed in newer version',
        isLocked: i1.is_locked,
      });
    } else {
      const i2 = v2Entry.item;
      const isChanged =
        i1.title !== i2.title ||
        i1.start_time !== i2.start_time ||
        i1.end_time !== i2.end_time ||
        i1.est_cost !== i2.est_cost ||
        d1 !== v2Entry.day;

      if (isChanged) {
        rows.push({
          key,
          op: 'replace',
          day: v2Entry.day,
          before: {
            title: i1.title,
            start: i1.start_time,
            end: i1.end_time,
            cost: i1.est_cost,
            is_locked: i1.is_locked,
            flags: i1.flags,
          },
          after: {
            title: i2.title,
            start: i2.start_time,
            end: i2.end_time,
            cost: i2.est_cost,
            is_locked: i2.is_locked,
            flags: i2.flags,
          },
          why: d1 !== v2Entry.day ? `Moved from Day ${d1} to Day ${v2Entry.day}` : 'Schedule or place updated',
          isLocked: i2.is_locked,
        });
      } else {
        rows.push({
          key,
          op: 'unchanged',
          day: d1,
          before: {
            title: i1.title,
            start: i1.start_time,
            end: i1.end_time,
            cost: i1.est_cost,
            is_locked: i1.is_locked,
            flags: i1.flags,
          },
          after: {
            title: i2.title,
            start: i2.start_time,
            end: i2.end_time,
            cost: i2.est_cost,
            is_locked: i2.is_locked,
            flags: i2.flags,
          },
          isLocked: i1.is_locked,
        });
      }
    }
  });

  // Check items added in V2
  mapV2.forEach(({ item: i2, day: d2 }, key) => {
    if (!mapV1.has(key)) {
      rows.push({
        key,
        op: 'add',
        day: d2,
        after: {
          title: i2.title,
          start: i2.start_time,
          end: i2.end_time,
          cost: i2.est_cost,
          is_locked: i2.is_locked,
          flags: i2.flags,
        },
        why: 'Added in newer version',
        isLocked: i2.is_locked,
      });
    }
  });

  return rows.sort((a, b) => a.day - b.day);
}
