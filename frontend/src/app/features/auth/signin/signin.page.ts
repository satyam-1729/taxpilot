import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'app-signin-page',
  standalone: true,
  imports: [FormsModule],
  template: `
    <main class="bg-background min-h-screen pt-12 pb-20 flex flex-col items-center px-4">
      <div class="w-full max-w-5xl flex flex-col md:flex-row gap-12 items-center">

        <!-- Left: Trust Branding -->
        <div class="flex-1 space-y-8 text-left">
          <div class="space-y-4">
            <span class="inline-flex items-center gap-2 px-3 py-1 bg-secondary-container text-on-secondary-container rounded-full text-xs font-semibold tracking-wide uppercase">
              <span class="material-symbols-outlined text-[14px]" style="font-variation-settings: 'FILL' 1;">verified_user</span>
              Bank-Grade Encryption
            </span>
            <h1 class="font-display text-4xl md:text-5xl font-extrabold text-primary leading-[1.1] tracking-tight">
              Simplify Your Taxes.
              <br>
              <span class="text-secondary">Maximize Your Savings.</span>
            </h1>
            <p class="text-on-surface-variant text-lg max-w-md leading-relaxed">
              The smartest way for Indians to file taxes, manage investments, and save more, all in one place.
            </p>
          </div>

          <div class="flex flex-col gap-6">
            <div class="flex items-start gap-4 p-4 rounded-xl bg-surface-container-low transition-all hover:bg-surface-container">
              <div class="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center shadow-sm">
                <span class="material-symbols-outlined text-primary">lock</span>
              </div>
              <div>
                <h3 class="font-headline font-bold text-primary">Biometric Security</h3>
                <p class="text-on-surface-variant text-sm">Protected by advanced multi-factor authentication.</p>
              </div>
            </div>
            <div class="flex items-start gap-4 p-4 rounded-xl bg-surface-container-low transition-all hover:bg-surface-container">
              <div class="w-10 h-10 rounded-lg bg-surface-container-lowest flex items-center justify-center shadow-sm">
                <span class="material-symbols-outlined text-secondary">shield</span>
              </div>
              <div>
                <h3 class="font-headline font-bold text-primary">Regulatory Compliance</h3>
                <p class="text-on-surface-variant text-sm">Fully audited and compliant with global financial standards.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Sign-In Card -->
        <div class="w-full max-w-md">
          <div class="bg-surface-container-lowest p-8 md:p-10 rounded-[2rem] shadow-[0_24px_48px_rgba(0,6,102,0.06)] relative overflow-hidden">
            <div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-primary/5 to-transparent rounded-bl-full"></div>

            <div class="relative z-10">
              <div class="mb-10 flex flex-col items-center text-center">
                <div class="w-14 h-14 rounded-2xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20 mb-5">
                  <span class="text-white font-display font-extrabold text-xl tracking-[-0.04em]">TP</span>
                </div>
                <p class="font-display text-base font-semibold text-on-surface-variant">
                  Continue to <span class="font-wordmark font-extrabold tracking-tight text-primary">TaxPilot</span>
                </p>
              </div>

              @if (error()) {
                <div class="mb-6 px-4 py-3 rounded-xl bg-error-container text-on-error-container text-sm">
                  {{ error() }}
                </div>
              }

              <div class="space-y-6">

                @if (step() === 'phone') {
                  <!-- Mobile Number -->
                  <div class="space-y-4">
                    <label class="block text-xs font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="phone">
                      Mobile Number
                    </label>
                    <div class="relative group">
                      <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <span class="text-on-surface-variant font-medium text-sm">+91</span>
                      </div>
                      <input
                        id="phone"
                        type="tel"
                        autocomplete="tel"
                        placeholder="Enter mobile number"
                        class="w-full bg-surface-container-lowest border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-4 pl-14 pr-4 transition-all outline-none text-on-surface font-medium placeholder:text-outline"
                        [(ngModel)]="phone"
                        [disabled]="busy()"
                      />
                    </div>
                    <button
                      type="button"
                      class="w-full bg-gradient-to-r from-primary to-primary-container text-white py-4 rounded-xl font-headline font-bold shadow-lg shadow-primary/10 hover:opacity-95 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                      (click)="requestOtp()"
                      [disabled]="!canRequestOtp() || busy()"
                    >
                      {{ busy() ? 'Sending…' : 'Send OTP' }}
                    </button>
                  </div>
                }

                @if (step() === 'otp') {
                  <div class="space-y-4">
                    <label class="block text-xs font-bold text-on-surface-variant uppercase tracking-widest ml-1" for="otp">
                      Enter 6-digit code sent to +91 {{ phone }}
                    </label>
                    <input
                      id="otp"
                      type="text"
                      inputmode="numeric"
                      maxlength="6"
                      autocomplete="one-time-code"
                      placeholder="000000"
                      class="w-full bg-surface-container-lowest border-0 ring-1 ring-outline-variant/30 focus:ring-2 focus:ring-primary rounded-xl py-4 px-4 transition-all outline-none text-on-surface font-display font-bold text-2xl tracking-[0.5em] text-center placeholder:text-outline"
                      [(ngModel)]="code"
                      [disabled]="busy()"
                    />
                    <button
                      type="button"
                      class="w-full bg-gradient-to-r from-primary to-primary-container text-white py-4 rounded-xl font-headline font-bold shadow-lg shadow-primary/10 hover:opacity-95 transition-all transform active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                      (click)="verifyOtp()"
                      [disabled]="code.length !== 6 || busy()"
                    >
                      {{ busy() ? 'Verifying…' : 'Verify & continue' }}
                    </button>
                    <button
                      type="button"
                      class="w-full text-on-surface-variant text-xs font-medium hover:text-primary transition-colors"
                      (click)="resetToPhone()"
                      [disabled]="busy()"
                    >
                      Use a different mobile number
                    </button>
                  </div>
                }

                <!-- Divider -->
                <div class="relative flex items-center py-4">
                  <div class="flex-grow border-t border-outline-variant/20"></div>
                  <span class="flex-shrink mx-4 text-outline text-xs font-bold uppercase tracking-widest">or</span>
                  <div class="flex-grow border-t border-outline-variant/20"></div>
                </div>

                <!-- Google Sign In -->
                <button
                  type="button"
                  class="w-full flex items-center justify-center gap-3 bg-surface-container-lowest border-0 ring-1 ring-outline-variant/30 hover:bg-surface-container-low py-4 rounded-xl transition-all group disabled:opacity-50 disabled:cursor-not-allowed"
                  (click)="signInWithGoogle()"
                  [disabled]="busy()"
                >
                  <svg viewBox="0 0 18 18" width="20" height="20" aria-hidden="true">
                    <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84c-.21 1.13-.85 2.08-1.81 2.72v2.26h2.92c1.71-1.57 2.69-3.89 2.69-6.62z"/>
                    <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A8.997 8.997 0 0 0 9 18z"/>
                    <path fill="#FBBC05" d="M3.97 10.71A5.41 5.41 0 0 1 3.68 9c0-.59.1-1.17.28-1.71V4.96H.96A8.997 8.997 0 0 0 0 9c0 1.45.35 2.83.96 4.04l3.01-2.33z"/>
                    <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A8.997 8.997 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
                  </svg>
                  <span class="font-headline font-semibold text-primary text-sm group-hover:text-primary-container">
                    Sign in with Google
                  </span>
                </button>
              </div>
            </div>
          </div>

          <!-- Compliance badges -->
          <div class="mt-8 flex justify-center items-center gap-8 opacity-50 hover:opacity-100 transition-opacity duration-500">
            <span class="text-xs font-semibold tracking-wider text-on-surface-variant uppercase">PCI&nbsp;DSS</span>
            <span class="text-xs font-semibold tracking-wider text-on-surface-variant uppercase">ISO&nbsp;27001</span>
            <span class="text-xs font-semibold tracking-wider text-on-surface-variant uppercase">SOC&nbsp;2</span>
          </div>
        </div>
      </div>

      <div id="signin-recaptcha" class="hidden"></div>
    </main>

    <!-- Footer -->
    <footer class="bg-surface-container-low w-full py-12 px-8">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-7xl mx-auto border-t border-surface-variant pt-8">
        <div class="space-y-4">
          <span class="font-wordmark font-extrabold tracking-tight text-primary text-lg">TaxPilot</span>
          <p class="font-body text-sm leading-relaxed text-on-surface-variant opacity-80 max-w-sm">
            © 2026 Winter Technologies Pvt. Ltd. All rights reserved.
          </p>
        </div>
        <div class="flex flex-wrap gap-x-8 gap-y-4 md:justify-end items-center">
          <a class="text-on-surface-variant font-body text-sm hover:text-primary underline underline-offset-4 transition-opacity opacity-80 hover:opacity-100" href="#">Privacy Policy</a>
          <a class="text-on-surface-variant font-body text-sm hover:text-primary underline underline-offset-4 transition-opacity opacity-80 hover:opacity-100" href="#">Terms of Service</a>
          <a class="text-on-surface-variant font-body text-sm hover:text-primary underline underline-offset-4 transition-opacity opacity-80 hover:opacity-100" href="#">Security</a>
          <a class="text-on-surface-variant font-body text-sm hover:text-primary underline underline-offset-4 transition-opacity opacity-80 hover:opacity-100" href="#">Tax Guides</a>
        </div>
      </div>
    </footer>
  `,
})
export class SigninPage {
  step = signal<'phone' | 'otp'>('phone');
  busy = signal(false);
  error = signal<string | null>(null);
  phone = '';
  code = '';

  constructor(private auth: AuthService, private router: Router) {}

  canRequestOtp(): boolean {
    const digits = this.phone.replace(/\D/g, '');
    return digits.length >= 10;
  }

  async requestOtp(): Promise<void> {
    this.error.set(null);
    this.busy.set(true);
    try {
      const e164 = this.toE164(this.phone);
      await this.auth.sendPhoneOtp(e164, 'signin-recaptcha');
      this.step.set('otp');
    } catch (e: any) {
      this.error.set(this.humanize(e?.message ?? 'Could not send OTP. Try again.'));
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
      this.error.set(this.humanize(e?.message ?? 'Invalid code. Try again.'));
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
      this.error.set(this.humanize(e?.message ?? 'Google sign-in failed.'));
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
    void this.router.navigateByUrl(dest);
  }

  private toE164(input: string): string {
    const digits = input.replace(/\D/g, '');
    if (input.trim().startsWith('+')) return '+' + digits;
    if (digits.length === 10) return `+91${digits}`;
    return `+${digits}`;
  }

  private humanize(msg: string): string {
    if (msg.includes('billing-not-enabled')) {
      return 'Phone OTP requires Firebase Blaze plan. Try Google sign-in instead.';
    }
    if (msg.includes('captcha-check-failed')) {
      return 'reCAPTCHA failed. Make sure you opened the page on http://localhost:4200.';
    }
    if (msg.includes('popup-closed-by-user')) {
      return 'Sign-in popup was closed before completing.';
    }
    return msg;
  }
}
