/**
 * Global "privacy mode" — when on, all currency numbers across the app are
 * rendered as bullets (•••• / ₹••••) so the screen is safe to share. State
 * lives in a single Angular signal + localStorage; module-level helpers read
 * the signal so any computed/template that depends on them reactively updates.
 */

import { signal } from '@angular/core';

const STORAGE_KEY = 'tp_privacy';

function readInitial(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

/** Read this signal anywhere you want a re-render on toggle. */
export const privacyMode = signal<boolean>(readInitial());

export function togglePrivacy(): void {
  const next = !privacyMode();
  privacyMode.set(next);
  try {
    localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
  } catch {
    /* ignore — storage might be blocked in private mode */
  }
}

const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const MASKED_FULL = '₹******';
const MASKED_COMPACT = '₹****';

/** Format an INR amount; returns bullets when privacy mode is on. */
export function formatINR(value: number | string | null | undefined): string {
  if (privacyMode()) {
    if (value == null || value === '') return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return MASKED_FULL;
  }
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  if (n === 0) return '₹0';
  return INR.format(n);
}

/** Compact INR (₹1.5L, ₹12K) for axis labels; bullets in privacy mode. */
export function compactINR(value: number | null | undefined): string {
  if (privacyMode()) {
    if (value == null) return '—';
    const n = Math.abs(Number(value));
    if (!Number.isFinite(n)) return '—';
    return MASKED_COMPACT;
  }
  if (value == null) return '—';
  const n = Math.abs(Number(value));
  if (!Number.isFinite(n)) return '—';
  if (n >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
  if (n >= 1e3) return `₹${(value / 1e3).toFixed(1)}K`;
  return `₹${value}`;
}
