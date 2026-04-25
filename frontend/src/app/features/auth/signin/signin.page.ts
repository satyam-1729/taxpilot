import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-signin-page',
  standalone: true,
  imports: [FormsModule],
  template: `
    <main class="page">
      <section class="card">
        <h1>Sign in to TaxPilot</h1>
        <p class="lede">File your ITR in minutes — secure, AI-assisted.</p>

        @if (error()) { <p class="error">{{ error() }}</p> }

        @if (step() === 'phone') {
          <label>
            <span>Phone number</span>
            <input
              type="tel"
              placeholder="+91 98765 43210"
              [(ngModel)]="phone"
              [disabled]="busy()"
              autocomplete="tel"
            />
          </label>
          <button class="primary" (click)="requestOtp()" [disabled]="!canRequestOtp() || busy()">
            {{ busy() ? 'Sending…' : 'Send OTP' }}
          </button>
        }

        @if (step() === 'otp') {
          <label>
            <span>Enter the 6-digit code sent to {{ phone }}</span>
            <input
              type="text"
              inputmode="numeric"
              maxlength="6"
              placeholder="000000"
              [(ngModel)]="code"
              [disabled]="busy()"
              autocomplete="one-time-code"
            />
          </label>
          <button class="primary" (click)="verifyOtp()" [disabled]="code.length !== 6 || busy()">
            {{ busy() ? 'Verifying…' : 'Verify & continue' }}
          </button>
          <button class="link" (click)="resetToPhone()" [disabled]="busy()">Change phone number</button>
        }

        <div class="divider"><span>or</span></div>

        <button class="google" (click)="signInWithGoogle()" [disabled]="busy()">
          <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
            <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84c-.21 1.13-.85 2.08-1.81 2.72v2.26h2.92c1.71-1.57 2.69-3.89 2.69-6.62z"/>
            <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A8.997 8.997 0 0 0 9 18z"/>
            <path fill="#FBBC05" d="M3.97 10.71A5.41 5.41 0 0 1 3.68 9c0-.59.1-1.17.28-1.71V4.96H.96A8.997 8.997 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"/>
            <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A8.997 8.997 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
          </svg>
          <span>Continue with Google</span>
        </button>

        <p class="small">
          By continuing you agree to our Terms and Privacy Policy.
        </p>

        <div id="signin-recaptcha"></div>
      </section>
    </main>
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
    .page { max-width: 420px; margin: 0 auto; padding: 64px 20px 48px; }
    .card {
      background: #fff; border-radius: 20px; padding: 32px;
      box-shadow: 0 4px 24px rgba(0,6,102,0.04);
      display: flex; flex-direction: column; gap: 16px;
      font-family: 'Inter', system-ui, sans-serif;
    }
    h1 {
      font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 24px;
      color: #000666; margin: 0; letter-spacing: -0.02em;
    }
    .lede { color: #454652; font-size: 14px; margin: 0 0 8px; }
    label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: #454652; font-weight: 500; }
    input {
      height: 48px; border: 0; background: #f3f3f5; border-radius: 12px;
      padding: 0 14px; font-size: 15px; color: #1a1c1d;
      font-family: inherit; outline: none; transition: box-shadow .15s;
    }
    input:focus { box-shadow: 0 0 0 2px rgba(0,6,102,0.2); }
    input:disabled { opacity: 0.5; }
    button { font-family: 'Manrope', sans-serif; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .primary {
      height: 48px; border: 0; border-radius: 12px;
      background: #000666; color: #fff; font-size: 15px;
      transition: background .15s;
    }
    .primary:not(:disabled):hover { background: #1a237e; }
    .link { background: none; border: 0; color: #000666; font-size: 13px; padding: 4px; align-self: flex-start; }
    .google {
      height: 48px; border: 1px solid rgba(69,70,82,0.2); background: #fff;
      border-radius: 12px; display: flex; align-items: center; justify-content: center; gap: 10px;
      color: #1a1c1d; font-size: 14px;
    }
    .google:not(:disabled):hover { background: #f3f3f5; }
    .divider {
      display: flex; align-items: center; gap: 12px; color: #98989f; font-size: 12px; margin: 4px 0;
    }
    .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: rgba(69,70,82,0.15); }
    .small { font-size: 12px; color: #98989f; text-align: center; margin: 8px 0 0; }
    .error {
      background: rgba(220,38,38,0.08); color: #b91c1c; border-radius: 10px;
      padding: 10px 12px; font-size: 13px; margin: 0;
    }
  `]
})
export class SigninPage {
  step = signal<'phone' | 'otp'>('phone');
  busy = signal(false);
  error = signal<string | null>(null);
  phone = '';
  code = '';

  constructor(private auth: AuthService, private router: Router) {}

  canRequestOtp(): boolean {
    return /^\+?\d[\d\s-]{8,}$/.test(this.phone.trim());
  }

  async requestOtp(): Promise<void> {
    this.error.set(null);
    this.busy.set(true);
    try {
      const e164 = this.toE164(this.phone);
      await this.auth.sendPhoneOtp(e164, 'signin-recaptcha');
      this.step.set('otp');
    } catch (e: any) {
      this.error.set(e?.message ?? 'Could not send OTP. Try again.');
    } finally {
      this.busy.set(false);
    }
  }

  async verifyOtp(): Promise<void> {
    this.error.set(null);
    this.busy.set(true);
    try {
      await this.auth.confirmPhoneOtp(this.code);
      this.routeAfterAuth();
    } catch (e: any) {
      this.error.set(e?.message ?? 'Invalid code. Try again.');
    } finally {
      this.busy.set(false);
    }
  }

  async signInWithGoogle(): Promise<void> {
    this.error.set(null);
    this.busy.set(true);
    try {
      await this.auth.signInWithGoogle();
      this.routeAfterAuth();
    } catch (e: any) {
      this.error.set(e?.message ?? 'Google sign-in failed.');
    } finally {
      this.busy.set(false);
    }
  }

  resetToPhone(): void {
    this.code = '';
    this.step.set('phone');
  }

  private routeAfterAuth(): void {
    const dest = this.auth.isVerified() ? '/dashboard' : '/identity';
    this.router.navigateByUrl(dest);
  }

  private toE164(input: string): string {
    const trimmed = input.trim().replace(/[\s-]/g, '');
    if (trimmed.startsWith('+')) return trimmed;
    // Default to India country code if user typed bare 10-digit number
    if (/^\d{10}$/.test(trimmed)) return `+91${trimmed}`;
    return `+${trimmed}`;
  }
}
