import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { postKyc } from '../../../core/auth/api';
import { AuthService } from '../../../core/auth/auth.service';

const PAN_RE = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const AADHAAR_RE = /^\d{12}$/;

// Reasonable bounds: at least 18 years old, no older than 120
const TODAY = new Date();
const MIN_DOB = new Date(TODAY.getFullYear() - 120, 0, 1).toISOString().slice(0, 10);
const MAX_DOB = new Date(TODAY.getFullYear() - 18, TODAY.getMonth(), TODAY.getDate())
  .toISOString().slice(0, 10);

@Component({
  selector: 'app-identity-page',
  standalone: true,
  imports: [FormsModule],
  template: `
    <main class="page">
      <section class="card">
        <span class="badge">One-time KYC</span>
        <h1>Verify your identity</h1>
        <p class="lede">
          A one-time check before we file your taxes. Stored encrypted — you won't
          be asked again.
        </p>

        @if (error()) { <p class="error">{{ error() }}</p> }

        <label>
          <span>Full name (as on PAN)</span>
          <input
            type="text"
            placeholder="Your full legal name"
            maxlength="200"
            [(ngModel)]="name"
            [disabled]="busy()"
            autocomplete="name"
          />
        </label>

        <label>
          <span>Date of birth</span>
          <input
            type="date"
            [min]="MIN_DOB"
            [max]="MAX_DOB"
            [(ngModel)]="dob"
            [disabled]="busy()"
            autocomplete="bday"
          />
          <small>Used to auto-unlock password-protected Form 16 PDFs later.</small>
        </label>

        <label>
          <span>PAN</span>
          <input
            type="text"
            placeholder="ABCDE1234F"
            maxlength="10"
            [(ngModel)]="pan"
            (ngModelChange)="pan = $event?.toUpperCase() ?? ''"
            [disabled]="busy()"
            autocomplete="off"
          />
        </label>

        <label>
          <span>Aadhaar number</span>
          <input
            type="text"
            inputmode="numeric"
            placeholder="0000 0000 0000"
            maxlength="14"
            [(ngModel)]="aadhaar"
            (ngModelChange)="formatAadhaar($event)"
            [disabled]="busy()"
            autocomplete="off"
          />
          <small>12 digits, no spaces required.</small>
        </label>

        <button class="primary" (click)="submit()" [disabled]="!canSubmit() || busy()">
          {{ busy() ? 'Verifying…' : 'Verify & continue' }}
        </button>

        <button class="link" (click)="signOut()" [disabled]="busy()">Sign out</button>
      </section>
    </main>
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
    .page { max-width: 460px; margin: 0 auto; padding: 64px 20px 48px; }
    .card {
      background: #fff; border-radius: 20px; padding: 32px;
      box-shadow: 0 4px 24px rgba(0,6,102,0.04);
      display: flex; flex-direction: column; gap: 16px;
      font-family: 'Inter', system-ui, sans-serif;
    }
    .badge {
      align-self: flex-start; background: #e0e0ff; color: #000666;
      font-family: 'Manrope', sans-serif; font-size: 11px; font-weight: 700;
      letter-spacing: 0.08em; text-transform: uppercase;
      padding: 4px 10px; border-radius: 999px;
    }
    h1 {
      font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 24px;
      color: #000666; margin: 0; letter-spacing: -0.02em;
    }
    .lede { color: #454652; font-size: 14px; margin: 0 0 8px; line-height: 1.5; }
    label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #454652; font-weight: 500; }
    label small { color: #98989f; font-size: 11px; font-weight: 400; }
    input {
      height: 48px; border: 0; background: #f3f3f5; border-radius: 12px;
      padding: 0 14px; font-size: 15px; color: #1a1c1d;
      font-family: 'Manrope', sans-serif; font-weight: 700; letter-spacing: 0.04em;
      outline: none; transition: box-shadow .15s;
    }
    input:focus { box-shadow: 0 0 0 2px rgba(0,6,102,0.2); }
    input:disabled { opacity: 0.5; }
    button { font-family: 'Manrope', sans-serif; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .primary {
      height: 48px; border: 0; border-radius: 12px;
      background: #000666; color: #fff; font-size: 15px; margin-top: 8px;
      transition: background .15s;
    }
    .primary:not(:disabled):hover { background: #1a237e; }
    .link { background: none; border: 0; color: #454652; font-size: 13px; padding: 4px; align-self: center; }
    .error {
      background: rgba(220,38,38,0.08); color: #b91c1c; border-radius: 10px;
      padding: 10px 12px; font-size: 13px; margin: 0;
    }
  `]
})
export class IdentityPage {
  busy = signal(false);
  error = signal<string | null>(null);
  name = '';
  dob = '';   // YYYY-MM-DD from <input type="date">
  pan = '';
  aadhaar = '';

  readonly MIN_DOB = MIN_DOB;
  readonly MAX_DOB = MAX_DOB;

  constructor(private auth: AuthService, private router: Router) {}

  canSubmit(): boolean {
    return (
      this.name.trim().length > 0 &&
      this.isValidDob(this.dob) &&
      PAN_RE.test(this.pan.trim()) &&
      AADHAAR_RE.test(this.rawAadhaar())
    );
  }

  formatAadhaar(value: string): void {
    const digits = (value ?? '').replace(/\D/g, '').slice(0, 12);
    this.aadhaar = digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
  }

  async submit(): Promise<void> {
    this.error.set(null);
    const token = this.auth.token();
    if (!token) {
      this.router.navigateByUrl('/signin');
      return;
    }
    this.busy.set(true);
    try {
      const user = await postKyc(token, {
        name: this.name.trim(),
        dob: this.dob,
        pan: this.pan.trim(),
        aadhaar: this.rawAadhaar(),
      });
      this.auth.setUser(user);
      this.router.navigateByUrl('/dashboard');
    } catch (e: any) {
      this.error.set(e?.message ?? 'Verification failed. Check your details and try again.');
    } finally {
      this.busy.set(false);
    }
  }

  async signOut(): Promise<void> {
    await this.auth.signOut();
    this.router.navigateByUrl('/signin');
  }

  private rawAadhaar(): string {
    return this.aadhaar.replace(/\s+/g, '');
  }

  private isValidDob(value: string): boolean {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    return value >= MIN_DOB && value <= MAX_DOB;
  }
}
