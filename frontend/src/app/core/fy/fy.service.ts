import { Injectable, computed, signal } from '@angular/core';

import { DocumentRow } from '../documents/documents.api';

const STORAGE_KEY = 'taxpilot.selectedFy';

/**
 * Global financial-year selector. Each page registers the documents it has
 * loaded; the service merges their FYs into a shared dropdown and keeps the
 * user's selection consistent across navigation. Selected FY persists to
 * localStorage so it survives reloads.
 *
 * Pages should:
 *   - inject FyService
 *   - call register(docs) after loading documents
 *   - read selectedFy() and filter their data by it
 */
@Injectable({ providedIn: 'root' })
export class FyService {
  /** All FYs seen across docs registered so far. */
  private readonly _availableFys = signal<string[]>([]);
  readonly availableFys = computed(() => this._availableFys());

  /** Currently-selected FY. Empty string means "nothing selected yet". */
  private readonly _selectedFy = signal<string>(this.loadFromStorage());
  readonly selectedFy = computed(() => this._selectedFy());

  setSelectedFy(fy: string): void {
    this._selectedFy.set(fy);
    if (typeof localStorage !== 'undefined') {
      try {
        if (fy) localStorage.setItem(STORAGE_KEY, fy);
        else localStorage.removeItem(STORAGE_KEY);
      } catch {
        // localStorage disabled (private mode); selection is then tab-local.
      }
    }
  }

  /**
   * Add the FYs visible in `docs` to the available list. Pages call this
   * after their initial load. Idempotent — repeated calls converge on the
   * same set, and the most recent FY is auto-selected if nothing is selected.
   */
  register(docs: DocumentRow[]): void {
    const merged = new Set(this._availableFys());
    for (const d of docs) {
      if (d.status !== 'parsed') continue;
      const fy = fyOf(d);
      if (fy) merged.add(fy);
    }
    const sorted = Array.from(merged).sort().reverse();
    this._availableFys.set(sorted);

    // Auto-select the most recent FY if nothing chosen, or fix up an invalid
    // selection (e.g. user deleted the doc that contributed the selected FY).
    const cur = this._selectedFy();
    if (!cur || !sorted.includes(cur)) {
      if (sorted.length > 0) this.setSelectedFy(sorted[0]);
    }
  }

  /** Strip out FYs sourced from documents the page no longer wants to count. */
  resetAvailableFys(): void {
    this._availableFys.set([]);
  }

  private loadFromStorage(): string {
    if (typeof localStorage === 'undefined') return '';
    try {
      return localStorage.getItem(STORAGE_KEY) ?? '';
    } catch {
      return '';
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers — exported so pages can reuse the same FY-extraction logic.
// ─────────────────────────────────────────────────────────────────────────────

/** Extract the FY for a document row, falling back to deriving it from AY. */
export function fyOf(d: DocumentRow): string {
  return (d.parsed_json?.fy as string) || ayToFy(d.ay) || '';
}

/** AY "2026-27" → FY "2025-26". Returns '' for unparseable input. */
export function ayToFy(ay: string | null): string {
  if (!ay) return '';
  const m = ay.match(/^(\d{4})-(\d{2})$/);
  if (!m) return '';
  const fyStart = Number(m[1]) - 1;
  const fyEndShort = String(Number(m[2]) - 1).padStart(2, '0');
  return `${fyStart}-${fyEndShort}`;
}
