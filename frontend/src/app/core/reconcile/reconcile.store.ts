import { Injectable, computed, effect, inject, signal } from '@angular/core';

import { DocumentsStore } from '../documents/documents.store';
import { ReconcileResponse, fetchReconcile } from './reconcile.api';

/**
 * Per-FY cache for reconciliation findings.
 *
 * Recompute is expensive (server pulls every parsed doc, decrypts, diffs), so
 * we cache the response keyed by FY. Each cache entry carries the document
 * version it was computed against — when DocumentsStore bumps its version
 * (after an upload or delete), every cached entry is invalidated.
 *
 * Concurrent callers for the same FY share one request.
 */

interface CacheEntry {
  res: ReconcileResponse;
  version: number;
}

@Injectable({ providedIn: 'root' })
export class ReconcileStore {
  private readonly docsStore = inject(DocumentsStore);

  private readonly _byFy = signal<Map<string, CacheEntry>>(new Map());
  private readonly _loadingFys = signal<Set<string>>(new Set());

  private readonly inFlight = new Map<string, Promise<ReconcileResponse>>();

  readonly loading = computed(() => this._loadingFys().size > 0);

  constructor() {
    // When docs change, blow away cache entries computed against the old version.
    effect(() => {
      const v = this.docsStore.version();
      const next = new Map<string, CacheEntry>();
      for (const [fy, entry] of this._byFy()) {
        if (entry.version === v) next.set(fy, entry);
      }
      if (next.size !== this._byFy().size) this._byFy.set(next);
    });
  }

  byFy(fy: string): ReconcileResponse | undefined {
    return this._byFy().get(fy)?.res;
  }

  isLoading(fy: string): boolean {
    return this._loadingFys().has(fy);
  }

  async ensureFor(token: string, fy: string): Promise<ReconcileResponse | null> {
    if (!fy) return null;
    const cached = this._byFy().get(fy);
    if (cached && cached.version === this.docsStore.version()) return cached.res;

    const existing = this.inFlight.get(fy);
    if (existing) return existing;

    this._loadingFys.update(s => new Set(s).add(fy));
    const versionAtStart = this.docsStore.version();

    const p = fetchReconcile(token, fy)
      .then(res => {
        const next = new Map(this._byFy());
        next.set(fy, { res, version: versionAtStart });
        this._byFy.set(next);
        return res;
      })
      .finally(() => {
        this.inFlight.delete(fy);
        this._loadingFys.update(s => {
          const out = new Set(s);
          out.delete(fy);
          return out;
        });
      });

    this.inFlight.set(fy, p);
    return p;
  }

  /** Drop everything (e.g. on sign-out). */
  clear(): void {
    this._byFy.set(new Map());
  }
}
