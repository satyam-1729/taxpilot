import { Injectable, computed, signal } from '@angular/core';

import { DocumentRow, listDocuments } from './documents.api';

/**
 * App-wide cache for the user's documents list.
 *
 * - First page that needs docs calls `ensureLoaded()` — subsequent navigations
 *   read straight from the cache (no network round-trip).
 * - CRUD operations (upload / delete / decrypt) call `refresh()` so dependent
 *   stores (ReconcileStore, regime computations) re-derive automatically.
 * - Concurrent callers share one in-flight request so a fresh page mount
 *   never triggers a stampede.
 */
@Injectable({ providedIn: 'root' })
export class DocumentsStore {
  private readonly _docs = signal<DocumentRow[]>([]);
  private readonly _loaded = signal(false);
  private readonly _loading = signal(false);
  private readonly _error = signal<string | null>(null);
  /** Bumps on every successful refresh — downstream stores key their cache off this. */
  private readonly _version = signal(0);

  private inFlight: Promise<DocumentRow[]> | null = null;

  readonly docs = computed(() => this._docs());
  readonly loaded = computed(() => this._loaded());
  readonly loading = computed(() => this._loading());
  readonly error = computed(() => this._error());
  readonly version = computed(() => this._version());

  /** Returns cached docs synchronously if loaded; fetches once if not. */
  async ensureLoaded(token: string): Promise<DocumentRow[]> {
    if (this._loaded()) return this._docs();
    return this.refresh(token);
  }

  /** Force a refetch. Concurrent callers share one request. */
  async refresh(token: string): Promise<DocumentRow[]> {
    if (this.inFlight) return this.inFlight;
    this._loading.set(true);
    this._error.set(null);
    this.inFlight = listDocuments(token)
      .then(list => {
        this._docs.set(list);
        this._loaded.set(true);
        this._version.update(v => v + 1);
        return list;
      })
      .catch(err => {
        this._error.set(err?.message ?? 'Could not load documents');
        throw err;
      })
      .finally(() => {
        this._loading.set(false);
        this.inFlight = null;
      });
    return this.inFlight;
  }

  /** Optimistic in-memory mutation, e.g. after a delete. */
  setDocs(docs: DocumentRow[]): void {
    this._docs.set(docs);
    this._loaded.set(true);
    this._version.update(v => v + 1);
  }
}
