import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import {
  AccountType,
  BankAccount,
  addBankAccount,
  deleteBankAccount,
  listBankAccounts,
  makePrimaryBankAccount,
} from '../../core/profile/profile.api';

const IFSC_RE = /^[A-Z]{4}0[A-Z0-9]{6}$/;
const ACCOUNT_NUMBER_RE = /^\d{6,18}$/;

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [CommonModule, DatePipe, FormsModule],
  template: `
    <main class="max-w-3xl mx-auto px-6 py-10">
      @if (!user()) {
        <div class="bg-surface-container-low rounded-2xl p-10 text-center text-on-surface-variant">
          Loading…
        </div>
      } @else {
        <!-- Identity card -->
        <section class="bg-surface-container-lowest rounded-3xl p-8 mb-6 shadow-sm">
          <div class="flex items-center gap-5 mb-8">
            <div class="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
              <span class="text-white font-display font-extrabold text-2xl tracking-[-0.04em]">
                {{ initials() }}
              </span>
            </div>
            <div class="flex-1 min-w-0">
              <h2 class="font-headline font-extrabold text-primary text-2xl tracking-tight truncate">
                {{ user()!.name || 'Unnamed' }}
              </h2>
              <div class="flex items-center gap-2 mt-1">
                @if (user()!.verified) {
                  <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-xs font-bold">
                    <span class="material-symbols-outlined text-[14px]" style="font-variation-settings:'FILL' 1;">verified</span>
                    Verified
                  </span>
                  @if (user()!.verified_at) {
                    <span class="text-xs text-on-surface-variant">
                      {{ user()!.verified_at | date:'MMM d, yyyy' }}
                    </span>
                  }
                } @else {
                  <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-error-container text-on-error-container text-xs font-bold">
                    <span class="material-symbols-outlined text-[14px]">error</span>
                    Not verified
                  </span>
                }
              </div>
            </div>
          </div>

          <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Full name</dt>
              <dd class="font-headline font-semibold text-primary text-base">{{ user()!.name || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Date of birth</dt>
              <dd class="font-headline font-semibold text-primary text-base">
                {{ user()!.dob ? (user()!.dob | date:'d MMMM yyyy') : '—' }}
              </dd>
            </div>
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Phone</dt>
              <dd class="font-headline font-semibold text-primary text-base">{{ user()!.phone || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Email</dt>
              <dd class="font-headline font-semibold text-primary text-base break-all">{{ user()!.email || '—' }}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">PAN</dt>
              <dd class="font-mono font-bold text-primary text-base tracking-[0.15em]">{{ maskedPan() }}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Aadhaar</dt>
              <dd class="font-mono font-bold text-primary text-base tracking-[0.15em]">{{ maskedAadhaar() }}</dd>
            </div>
          </dl>
        </section>

        <!-- Bank accounts card -->
        <section class="bg-surface-container-lowest rounded-3xl p-8 mb-6 shadow-sm">
          <div class="flex items-center justify-between gap-4 mb-6 flex-wrap">
            <div>
              <h2 class="font-headline font-extrabold text-primary text-xl tracking-tight">Bank accounts</h2>
              <p class="text-sm text-on-surface-variant mt-1">
                Used for tax refunds. The primary account is where the IT department deposits.
              </p>
            </div>
            <button
              type="button"
              class="px-4 py-2 rounded-xl bg-primary text-white font-headline font-semibold text-sm hover:opacity-95 transition flex items-center gap-2"
              (click)="openAddBank()"
            >
              <span class="material-symbols-outlined text-[18px]">add</span>
              Add account
            </button>
          </div>

          @if (bankError()) {
            <p class="text-sm text-error bg-error-container/40 rounded-xl px-4 py-3 mb-4">{{ bankError() }}</p>
          }

          @if (bankLoading() && bankAccounts().length === 0) {
            <div class="text-on-surface-variant text-sm py-6">Loading…</div>
          } @else if (bankAccounts().length === 0) {
            <div class="bg-surface-container-low rounded-2xl p-8 text-center text-on-surface-variant">
              No bank accounts yet. Add one so refunds can land directly.
            </div>
          } @else {
            <ul class="space-y-3">
              @for (acc of bankAccounts(); track acc.id) {
                <li class="bg-surface-container-low rounded-2xl p-4 flex items-center gap-4">
                  <div class="w-12 h-12 rounded-xl bg-surface-container-lowest flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-primary">account_balance</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-headline font-bold text-primary truncate">{{ acc.bank_name }}</span>
                      @if (acc.is_primary) {
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container text-[10px] font-bold uppercase tracking-widest">
                          <span class="material-symbols-outlined text-[12px]" style="font-variation-settings:'FILL' 1;">star</span>
                          Primary
                        </span>
                      }
                    </div>
                    <div class="text-sm text-on-surface-variant mt-1 flex flex-wrap gap-x-3 gap-y-1">
                      <span class="font-mono tracking-wider">••••&nbsp;{{ acc.account_last4 }}</span>
                      <span>•</span>
                      <span class="font-mono">{{ acc.ifsc }}</span>
                      <span>•</span>
                      <span class="capitalize">{{ acc.account_type }}</span>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    @if (!acc.is_primary) {
                      <button
                        type="button"
                        class="px-3 py-1.5 rounded-lg text-on-surface-variant text-xs font-headline font-semibold hover:bg-surface-container transition"
                        (click)="setPrimary(acc.id)"
                        [disabled]="busyAccountId() === acc.id"
                      >
                        Make primary
                      </button>
                    }
                    <button
                      type="button"
                      class="w-9 h-9 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-error-container hover:text-on-error-container transition"
                      (click)="remove(acc.id)"
                      [disabled]="busyAccountId() === acc.id"
                      title="Delete"
                    >
                      <span class="material-symbols-outlined text-[20px]">delete</span>
                    </button>
                  </div>
                </li>
              }
            </ul>
          }
        </section>

        <!-- Account actions -->
        <section class="bg-surface-container-lowest rounded-3xl p-6 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="font-headline font-bold text-primary">Sign out</h3>
            <p class="text-sm text-on-surface-variant mt-1">
              You'll need to sign in again on this device.
            </p>
          </div>
          <button
            type="button"
            class="px-5 py-2.5 rounded-xl bg-error-container text-on-error-container font-headline font-semibold text-sm hover:opacity-95 transition"
            (click)="signOut()"
          >
            Sign out
          </button>
        </section>
      }
    </main>

    <!-- Add bank account modal -->
    @if (addModalOpen()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-sm"
           (click)="closeAddBank()">
        <div class="bg-surface-container-lowest rounded-3xl p-8 max-w-md w-full shadow-2xl"
             (click)="$event.stopPropagation()">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-10 h-10 rounded-xl bg-primary-fixed flex items-center justify-center">
              <span class="material-symbols-outlined text-primary">account_balance</span>
            </div>
            <h3 class="font-headline font-bold text-primary text-xl">Add bank account</h3>
          </div>
          <p class="text-sm text-on-surface-variant mb-5 leading-relaxed">
            Used for tax refunds. We encrypt the full account number — only the last 4 digits are shown.
          </p>

          @if (addError()) {
            <p class="text-error text-sm bg-error-container/40 rounded-xl px-3 py-2 mb-4">{{ addError() }}</p>
          }

          <div class="space-y-4">
            <label class="block">
              <span class="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2 block">Bank name</span>
              <input
                type="text"
                placeholder="e.g. HDFC Bank"
                class="w-full bg-surface-container-low border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-3 px-4 transition outline-none text-on-surface font-medium"
                [(ngModel)]="bankNameInput"
                [disabled]="adding()"
              />
            </label>

            <label class="block">
              <span class="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2 block">IFSC</span>
              <input
                type="text"
                placeholder="HDFC0001234"
                maxlength="11"
                class="w-full bg-surface-container-low border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-3 px-4 transition outline-none text-on-surface font-mono font-bold tracking-[0.15em]"
                [(ngModel)]="ifscInput"
                (ngModelChange)="ifscInput = $event?.toUpperCase() ?? ''"
                [disabled]="adding()"
              />
            </label>

            <label class="block">
              <span class="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2 block">Account number</span>
              <input
                type="text"
                inputmode="numeric"
                placeholder="6–18 digits"
                maxlength="18"
                class="w-full bg-surface-container-low border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-3 px-4 transition outline-none text-on-surface font-mono font-bold tracking-[0.15em]"
                [(ngModel)]="accountNumberInput"
                (ngModelChange)="onAccountNumberChange($event)"
                [disabled]="adding()"
              />
            </label>

            <label class="block">
              <span class="text-xs font-bold text-on-surface-variant uppercase tracking-widest mb-2 block">Account type</span>
              <div class="flex gap-2">
                @for (t of accountTypes; track t) {
                  <button
                    type="button"
                    class="flex-1 py-2.5 rounded-xl border text-sm font-headline font-semibold capitalize transition"
                    [class.border-primary]="accountTypeInput === t"
                    [class.bg-primary-fixed]="accountTypeInput === t"
                    [class.text-primary]="accountTypeInput === t"
                    [class.border-outline-variant]="accountTypeInput !== t"
                    [class.text-on-surface-variant]="accountTypeInput !== t"
                    (click)="accountTypeInput = t"
                    [disabled]="adding()"
                  >{{ t }}</button>
                }
              </div>
            </label>

            <label class="flex items-center gap-3 cursor-pointer mt-1">
              <input type="checkbox" class="w-4 h-4 rounded accent-primary" [(ngModel)]="setPrimaryInput" [disabled]="adding()" />
              <span class="text-sm text-on-surface-variant">Set as primary refund account</span>
            </label>
          </div>

          <div class="flex gap-3 mt-6">
            <button
              type="button"
              class="flex-1 px-4 py-3 rounded-xl bg-surface-container-low text-on-surface font-headline font-semibold hover:bg-surface-container transition"
              (click)="closeAddBank()"
              [disabled]="adding()"
            >Cancel</button>
            <button
              type="button"
              class="flex-1 px-4 py-3 rounded-xl bg-primary text-white font-headline font-bold shadow-lg shadow-primary/10 hover:opacity-95 transition disabled:opacity-50 disabled:cursor-not-allowed"
              (click)="confirmAddBank()"
              [disabled]="!canAdd() || adding()"
            >{{ adding() ? 'Saving…' : 'Save account' }}</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
  `],
})
export class ProfilePage implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly user = computed(() => this.auth.user());

  readonly bankAccounts = signal<BankAccount[]>([]);
  readonly bankLoading = signal(true);
  readonly bankError = signal<string | null>(null);
  readonly busyAccountId = signal<string | null>(null);

  // Add modal state
  readonly addModalOpen = signal(false);
  readonly adding = signal(false);
  readonly addError = signal<string | null>(null);
  bankNameInput = '';
  ifscInput = '';
  accountNumberInput = '';
  accountTypeInput: AccountType = 'savings';
  setPrimaryInput = false;
  readonly accountTypes: AccountType[] = ['savings', 'current'];

  readonly initials = computed(() => {
    const u = this.user();
    if (!u) return 'TP';
    if (u.name?.trim()) {
      const parts = u.name.trim().split(/\s+/);
      return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase() || 'TP';
    }
    if (u.email?.[0]) return u.email[0].toUpperCase();
    return 'TP';
  });

  readonly maskedPan = computed(() => {
    const last4 = this.user()?.pan_last4;
    return last4 ? `XXXXXX${last4}` : '—';
  });

  readonly maskedAadhaar = computed(() => {
    const last4 = this.user()?.aadhaar_last4;
    return last4 ? `XXXX XXXX ${last4}` : '—';
  });

  async ngOnInit(): Promise<void> {
    await this.auth.refresh();
    await this.refreshBankAccounts();
  }

  // ── Bank accounts ────────────────────────────────────────────────────────

  async refreshBankAccounts(): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    this.bankError.set(null);
    try {
      const list = await listBankAccounts(token);
      this.bankAccounts.set(list);
    } catch (e: any) {
      this.bankError.set(e?.message ?? 'Could not load bank accounts.');
    } finally {
      this.bankLoading.set(false);
    }
  }

  openAddBank(): void {
    this.addError.set(null);
    this.bankNameInput = '';
    this.ifscInput = '';
    this.accountNumberInput = '';
    this.accountTypeInput = 'savings';
    this.setPrimaryInput = false;
    this.addModalOpen.set(true);
  }

  closeAddBank(): void {
    if (this.adding()) return;
    this.addModalOpen.set(false);
  }

  canAdd(): boolean {
    return (
      this.bankNameInput.trim().length >= 2 &&
      IFSC_RE.test(this.ifscInput.trim()) &&
      ACCOUNT_NUMBER_RE.test(this.accountNumberInput.trim())
    );
  }

  onAccountNumberChange(value: string): void {
    this.accountNumberInput = (value ?? '').replace(/\D/g, '').slice(0, 18);
  }

  async confirmAddBank(): Promise<void> {
    const token = this.auth.token();
    if (!token || !this.canAdd()) return;
    this.addError.set(null);
    this.adding.set(true);
    try {
      const created = await addBankAccount(token, {
        bank_name: this.bankNameInput.trim(),
        ifsc: this.ifscInput.trim(),
        account_number: this.accountNumberInput.trim(),
        account_type: this.accountTypeInput,
        is_primary: this.setPrimaryInput,
      });
      this.addModalOpen.set(false);
      await this.refreshBankAccounts();
      // ensure newly-created shows up at top if marked primary
      void created;
    } catch (e: any) {
      this.addError.set(this.humanize(e?.message ?? 'Could not save account.'));
    } finally {
      this.adding.set(false);
    }
  }

  async setPrimary(id: string): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    this.busyAccountId.set(id);
    this.bankError.set(null);
    try {
      await makePrimaryBankAccount(token, id);
      await this.refreshBankAccounts();
    } catch (e: any) {
      this.bankError.set(e?.message ?? 'Could not update primary.');
    } finally {
      this.busyAccountId.set(null);
    }
  }

  async remove(id: string): Promise<void> {
    if (!confirm('Remove this bank account?')) return;
    const token = this.auth.token();
    if (!token) return;
    this.busyAccountId.set(id);
    this.bankError.set(null);
    try {
      await deleteBankAccount(token, id);
      await this.refreshBankAccounts();
    } catch (e: any) {
      this.bankError.set(e?.message ?? 'Could not delete account.');
    } finally {
      this.busyAccountId.set(null);
    }
  }

  async signOut(): Promise<void> {
    await this.auth.signOut();
    await this.router.navigateByUrl('/signin');
  }

  private humanize(msg: string): string {
    if (msg.includes('IFSC')) return 'Check the IFSC — it must be 4 letters + 0 + 6 alphanumeric.';
    if (msg.includes('Account number')) return 'Account number must be 6–18 digits.';
    return msg;
  }
}
