import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../core/auth/auth.service';
import {
  DocumentRow,
  DocStatus,
  listDocuments,
  submitPassword,
  uploadDocument,
} from '../../core/documents/documents.api';

@Component({
  selector: 'app-documents-page',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  template: `
    <main class="max-w-5xl mx-auto px-6 py-10">
      <!-- Hero -->
      <section class="mb-10">
        <h1 class="font-display text-4xl md:text-5xl font-extrabold text-primary tracking-tight mb-3">
          Document Vault
        </h1>
        <p class="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
          Upload your Form 16 and we'll extract everything automatically — salary breakdown,
          TDS quarters, deductions with section codes — ready for your filing.
        </p>
      </section>

      <!-- Upload area -->
      <section
        class="bg-surface-container-lowest rounded-3xl p-10 mb-10 border-2 border-dashed transition-colors"
        [class.border-primary]="dragOver()"
        [class.border-outline-variant]="!dragOver()"
        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)"
      >
        <div class="flex flex-col items-center text-center gap-4">
          <div class="w-16 h-16 rounded-2xl bg-primary-fixed flex items-center justify-center">
            <span class="material-symbols-outlined text-primary text-3xl">upload_file</span>
          </div>
          <div>
            <h3 class="font-headline font-bold text-primary text-xl">Upload Form 16</h3>
            <p class="text-on-surface-variant text-sm mt-1">
              Drop a PDF here, or pick one from your computer. Up to 15 MB.
            </p>
          </div>

          <input
            #fileInput
            type="file"
            accept="application/pdf"
            class="hidden"
            (change)="onFilePicked($event)"
          />
          <button
            type="button"
            class="px-6 py-3 rounded-xl bg-primary text-white font-headline font-bold text-sm shadow-lg shadow-primary/10 hover:opacity-95 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
            (click)="fileInput.click()"
            [disabled]="uploading()"
          >
            {{ uploading() ? 'Uploading…' : 'Choose PDF' }}
          </button>

          @if (uploadError()) {
            <p class="text-error text-sm mt-2">{{ uploadError() }}</p>
          }
          @if (uploadInfo()) {
            <p class="text-secondary text-sm mt-2">{{ uploadInfo() }}</p>
          }
        </div>
      </section>

      <!-- Recent activity -->
      <section>
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-headline font-bold text-primary text-2xl">Recent activity</h2>
          @if (anyPending()) {
            <span class="text-xs font-semibold text-on-surface-variant uppercase tracking-wider flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              Live
            </span>
          }
        </div>

        @if (loading() && rows().length === 0) {
          <div class="text-center py-12 text-on-surface-variant text-sm">Loading…</div>
        } @else if (rows().length === 0) {
          <div class="bg-surface-container-low rounded-2xl p-10 text-center text-on-surface-variant">
            No documents yet. Upload your Form 16 above to get started.
          </div>
        } @else {
          <ul class="space-y-3">
            @for (row of rows(); track row.id) {
              <li class="bg-surface-container-lowest rounded-2xl p-5 flex items-start gap-4 shadow-sm hover:shadow-md transition-shadow">
                <!-- Status icon -->
                <div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                     [ngClass]="statusBg(row.status)">
                  @switch (row.status) {
                    @case ('queued') {
                      <span class="material-symbols-outlined text-on-surface-variant">schedule</span>
                    }
                    @case ('parsing') {
                      <span class="material-symbols-outlined text-primary animate-spin">progress_activity</span>
                    }
                    @case ('parsed') {
                      <span class="material-symbols-outlined text-secondary" style="font-variation-settings:'FILL' 1;">
                        check_circle
                      </span>
                    }
                    @case ('failed') {
                      <span class="material-symbols-outlined text-error" style="font-variation-settings:'FILL' 1;">
                        error
                      </span>
                    }
                    @case ('needs_password') {
                      <span class="material-symbols-outlined text-tertiary-container" style="font-variation-settings:'FILL' 1;">
                        lock
                      </span>
                    }
                  }
                </div>

                <!-- Body -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-headline font-bold text-primary truncate">{{ row.file_name }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                          [ngClass]="statusPill(row.status)">
                      {{ statusLabel(row.status) }}
                    </span>
                  </div>
                  <div class="text-sm text-on-surface-variant mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    <span>{{ formatBytes(row.file_size_bytes) }}</span>
                    <span>•</span>
                    <span>{{ row.created_at | date:'MMM d, h:mm a' }}</span>
                    @if (row.employer_name) {
                      <span>•</span>
                      <span class="truncate">{{ row.employer_name }}</span>
                    }
                    @if (row.ay) {
                      <span>•</span>
                      <span>AY {{ row.ay }}</span>
                    }
                  </div>
                  @if (row.status === 'parsed') {
                    <div class="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Gross salary</div>
                        <div class="font-headline font-bold text-primary">{{ formatINR(row.gross_salary) }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Total TDS</div>
                        <div class="font-headline font-bold text-primary">{{ formatINR(row.total_tds) }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Taxable income</div>
                        <div class="font-headline font-bold text-primary">{{ formatINR(row.taxable_income) }}</div>
                      </div>
                      <div>
                        <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Tax payable</div>
                        <div class="font-headline font-bold text-primary">{{ formatINR(row.tax_payable) }}</div>
                      </div>
                    </div>
                  }
                  @if (row.status === 'failed' && row.error) {
                    <p class="text-sm text-error mt-2">{{ row.error }}</p>
                  }
                  @if (row.status === 'needs_password') {
                    <button
                      type="button"
                      class="mt-3 px-4 py-2 rounded-lg bg-primary text-white text-sm font-headline font-semibold hover:opacity-95 transition"
                      (click)="openPasswordModal(row.id)"
                    >
                      Enter password
                    </button>
                  }
                </div>
              </li>
            }
          </ul>
        }
      </section>
    </main>

    <!-- Password modal -->
    @if (passwordPromptDocId()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-sm"
           (click)="closePasswordModal()">
        <div class="bg-surface-container-lowest rounded-3xl p-8 max-w-md w-full shadow-2xl"
             (click)="$event.stopPropagation()">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-xl bg-tertiary-container/40 flex items-center justify-center">
              <span class="material-symbols-outlined text-tertiary-container" style="font-variation-settings:'FILL' 1;">lock</span>
            </div>
            <h3 class="font-headline font-bold text-primary text-xl">Password required</h3>
          </div>
          <p class="text-sm text-on-surface-variant mb-6 leading-relaxed">
            This Form 16 PDF is password-protected. The default for most Indian employers is
            <span class="font-mono font-semibold text-primary">PAN[:5] + DOB(DDMMYYYY)</span>,
            e.g. <span class="font-mono">ABCDE01011990</span>.
          </p>
          <label class="block text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2" for="pwd">
            Password
          </label>
          <input
            id="pwd"
            #pwdInput
            type="password"
            placeholder="Enter password"
            class="w-full bg-surface-container-low border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-3 px-4 transition-all outline-none text-on-surface font-medium placeholder:text-outline"
            [(ngModel)]="passwordInput"
            (keyup.enter)="confirmPassword()"
            [disabled]="decrypting()"
          />
          @if (passwordError()) {
            <p class="text-error text-sm mt-2">{{ passwordError() }}</p>
          }
          <div class="flex gap-3 mt-6">
            <button
              type="button"
              class="flex-1 px-4 py-3 rounded-xl bg-surface-container-low text-on-surface font-headline font-semibold hover:bg-surface-container transition"
              (click)="closePasswordModal()"
              [disabled]="decrypting()"
            >
              Cancel
            </button>
            <button
              type="button"
              class="flex-1 px-4 py-3 rounded-xl bg-primary text-white font-headline font-bold shadow-lg shadow-primary/10 hover:opacity-95 transition disabled:opacity-50 disabled:cursor-not-allowed"
              (click)="confirmPassword()"
              [disabled]="!passwordInput || decrypting()"
            >
              {{ decrypting() ? 'Unlocking…' : 'Unlock & parse' }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
  `],
})
export class DocumentsPage implements OnInit, OnDestroy {
  private readonly auth = inject(AuthService);

  readonly rows = signal<DocumentRow[]>([]);
  readonly loading = signal(true);
  readonly uploading = signal(false);
  readonly uploadError = signal<string | null>(null);
  readonly uploadInfo = signal<string | null>(null);
  readonly dragOver = signal(false);

  // Password modal state
  readonly passwordPromptDocId = signal<string | null>(null);
  readonly passwordError = signal<string | null>(null);
  readonly decrypting = signal(false);
  passwordInput = '';

  readonly anyPending = computed(() =>
    this.rows().some(r => r.status === 'queued' || r.status === 'parsing'),
  );

  private pollHandle: ReturnType<typeof setTimeout> | null = null;

  async ngOnInit(): Promise<void> {
    await this.refresh();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  async refresh(): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    try {
      const data = await listDocuments(token);
      this.rows.set(data);
    } catch (e: any) {
      this.uploadError.set(e?.message ?? 'Could not load documents.');
    } finally {
      this.loading.set(false);
    }
    this.schedulePollIfNeeded();
  }

  private schedulePollIfNeeded(): void {
    this.stopPolling();
    if (this.anyPending()) {
      this.pollHandle = setTimeout(() => void this.refresh(), 2000);
    }
  }

  private stopPolling(): void {
    if (this.pollHandle) {
      clearTimeout(this.pollHandle);
      this.pollHandle = null;
    }
  }

  // ── Upload handlers ──────────────────────────────────────────────────────

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(e: DragEvent): void {
    e.preventDefault();
    this.dragOver.set(false);
  }

  async onDrop(e: DragEvent): Promise<void> {
    e.preventDefault();
    this.dragOver.set(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) await this.upload(file);
  }

  async onFilePicked(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) await this.upload(file);
    input.value = '';
  }

  private async upload(file: File): Promise<void> {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      this.uploadError.set('Only PDF files are supported.');
      return;
    }
    const token = this.auth.token();
    if (!token) {
      this.uploadError.set('Please sign in again.');
      return;
    }
    this.uploadError.set(null);
    this.uploadInfo.set(null);
    this.uploading.set(true);
    try {
      const res = await uploadDocument(token, file);
      if (res.status === 'needs_password') {
        this.uploadInfo.set('This PDF is password-protected — please enter the password.');
        this.openPasswordModal(res.id);
      } else if (res.deduplicated) {
        this.uploadInfo.set('This file was already uploaded — showing the existing parse.');
      } else {
        this.uploadInfo.set('Uploaded. Parsing in the background…');
      }
      await this.refresh();
    } catch (e: any) {
      this.uploadError.set(e?.message ?? 'Upload failed.');
    } finally {
      this.uploading.set(false);
    }
  }

  // ── Password modal ───────────────────────────────────────────────────────

  openPasswordModal(docId: string): void {
    this.passwordPromptDocId.set(docId);
    this.passwordError.set(null);
    this.passwordInput = '';
  }

  closePasswordModal(): void {
    if (this.decrypting()) return;
    this.passwordPromptDocId.set(null);
    this.passwordError.set(null);
    this.passwordInput = '';
  }

  async confirmPassword(): Promise<void> {
    const docId = this.passwordPromptDocId();
    const token = this.auth.token();
    if (!docId || !token || !this.passwordInput) return;
    this.passwordError.set(null);
    this.decrypting.set(true);
    try {
      await submitPassword(token, docId, this.passwordInput);
      this.passwordPromptDocId.set(null);
      this.passwordInput = '';
      this.uploadInfo.set('Unlocked. Parsing in the background…');
      await this.refresh();
    } catch (e: any) {
      const msg = e?.message ?? 'Could not unlock.';
      this.passwordError.set(msg.includes('Incorrect') ? 'Incorrect password — try again.' : msg);
    } finally {
      this.decrypting.set(false);
    }
  }

  // ── Display helpers ──────────────────────────────────────────────────────

  statusLabel(s: DocStatus): string {
    return {
      queued: 'Queued',
      parsing: 'Parsing',
      parsed: 'Parsed',
      failed: 'Failed',
      needs_password: 'Locked',
    }[s];
  }

  statusBg(s: DocStatus): string {
    return {
      queued: 'bg-surface-container-high',
      parsing: 'bg-primary-fixed',
      parsed: 'bg-secondary-container',
      failed: 'bg-error-container',
      needs_password: 'bg-tertiary-container/30',
    }[s];
  }

  statusPill(s: DocStatus): string {
    return {
      queued: 'bg-surface-container-high text-on-surface-variant',
      parsing: 'bg-primary-fixed text-primary',
      parsed: 'bg-secondary-container text-on-secondary-container',
      failed: 'bg-error-container text-on-error-container',
      needs_password: 'bg-tertiary-container/30 text-tertiary-container',
    }[s];
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  formatINR(value: string | null): string {
    if (value == null) return '—';
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(n);
  }
}
