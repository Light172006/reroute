// Formatting helpers for currency, times, dates, and durations

export function formatCurrency(amount: number, currency: string = 'INR'): string {
  const rounded = Math.round(amount);
  if (currency === 'INR') {
    return `Rs ${rounded.toLocaleString('en-IN')}`;
  }
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 0,
    }).format(rounded);
  } catch {
    return `${currency} ${rounded.toLocaleString()}`;
  }
}

export function formatDeltaCurrency(amount: number, currency: string = 'INR'): string {
  const sign = amount < 0 ? '-' : amount > 0 ? '+' : '';
  const absVal = Math.abs(Math.round(amount));
  if (currency === 'INR') {
    return `${sign}Rs ${absVal.toLocaleString('en-IN')}`;
  }
  try {
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 0,
    }).format(absVal);
    return `${sign}${formatted}`;
  } catch {
    return `${sign}${currency} ${absVal.toLocaleString()}`;
  }
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;
  if (remaining === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remaining}m`;
}

export function formatDateRange(startDateStr: string, endDateStr: string): string {
  try {
    const [y1, m1, d1] = startDateStr.split('-').map(Number);
    const [y2, m2, d2] = endDateStr.split('-').map(Number);

    const start = new Date(y1, (m1 || 1) - 1, d1 || 1);
    const end = new Date(y2, (m2 || 1) - 1, d2 || 1);

    const startMonth = start.toLocaleDateString('en-US', { month: 'short' });
    const endMonth = end.toLocaleDateString('en-US', { month: 'short' });
    const startDay = start.getDate();
    const endDay = end.getDate();
    const startYear = start.getFullYear();
    const endYear = end.getFullYear();

    if (startDateStr === endDateStr) {
      return `${startMonth} ${startDay}, ${startYear}`;
    }

    if (startYear !== endYear) {
      return `${startMonth} ${startDay}, ${startYear} - ${endMonth} ${endDay}, ${endYear}`;
    }

    if (startMonth === endMonth) {
      return `${startMonth} ${startDay} - ${endDay}, ${startYear}`;
    }
    return `${startMonth} ${startDay} - ${endMonth} ${endDay}, ${startYear}`;
  } catch {
    return `${startDateStr} - ${endDateStr}`;
  }
}

export function formatTime(timeStr: string): string {
  if (!timeStr) return '';
  return timeStr;
}

export function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}h ago`;
    const diffDays = Math.floor(diffHour / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}
