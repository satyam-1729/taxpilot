import { Injectable, computed, signal } from '@angular/core';
import {
  ConfirmationResult,
  GoogleAuthProvider,
  RecaptchaVerifier,
  signInWithPhoneNumber,
  signInWithPopup,
  signOut,
} from 'firebase/auth';

import { environment } from '../../../environments/environment';
import { firebaseAuth } from './firebase';

export interface AuthUser {
  id: string;
  phone: string | null;
  email: string | null;
  name: string | null;
  verified: boolean;
  verified_at: string | null;
}

interface StoredSession {
  token: string;
  user: AuthUser;
}

const STORAGE_KEY = 'tp_auth';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _session = signal<StoredSession | null>(this.readStorage());

  readonly user = computed(() => this._session()?.user ?? null);
  readonly token = computed(() => this._session()?.token ?? null);
  readonly isLoggedIn = computed(() => this._session() !== null);
  readonly isVerified = computed(() => this._session()?.user.verified ?? false);

  private confirmation: ConfirmationResult | null = null;
  private recaptcha: RecaptchaVerifier | null = null;

  /** Set up an invisible reCAPTCHA bound to a DOM element. Required before phone OTP. */
  ensureRecaptcha(containerId: string): RecaptchaVerifier {
    if (!this.recaptcha) {
      this.recaptcha = new RecaptchaVerifier(firebaseAuth(), containerId, { size: 'invisible' });
    }
    return this.recaptcha;
  }

  async sendPhoneOtp(phoneE164: string, recaptchaContainerId: string): Promise<void> {
    const verifier = this.ensureRecaptcha(recaptchaContainerId);
    this.confirmation = await signInWithPhoneNumber(firebaseAuth(), phoneE164, verifier);
  }

  async confirmPhoneOtp(code: string): Promise<void> {
    if (!this.confirmation) throw new Error('Request OTP first.');
    const cred = await this.confirmation.confirm(code);
    const idToken = await cred.user.getIdToken();
    await this.exchangeForSession(idToken);
  }

  async signInWithGoogle(): Promise<void> {
    const provider = new GoogleAuthProvider();
    const cred = await signInWithPopup(firebaseAuth(), provider);
    const idToken = await cred.user.getIdToken();
    await this.exchangeForSession(idToken);
  }

  async signOut(): Promise<void> {
    try {
      const token = this.token();
      if (token) {
        await fetch(`${environment.apiBaseUrl}/auth/logout`, {
          method: 'POST',
          headers: { authorization: `Bearer ${token}` },
        });
      }
    } catch { /* ignore network errors on logout */ }
    await signOut(firebaseAuth()).catch(() => undefined);
    this.clearSession();
  }

  /** After backend KYC, call this with the updated UserOut to keep local state in sync. */
  setUser(user: AuthUser): void {
    const current = this._session();
    if (!current) return;
    const next: StoredSession = { ...current, user };
    this._session.set(next);
    this.writeStorage(next);
  }

  /** Refetch /me using the stored token. Useful on app bootstrap. */
  async refresh(): Promise<void> {
    const token = this.token();
    if (!token) return;
    try {
      const res = await fetch(`${environment.apiBaseUrl}/auth/me`, {
        headers: { authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        this.clearSession();
        return;
      }
      const user: AuthUser = await res.json();
      this.setUser(user);
    } catch { /* keep cached session if /me is unreachable */ }
  }

  private async exchangeForSession(idToken: string): Promise<void> {
    const res = await fetch(`${environment.apiBaseUrl}/auth/session`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      throw new Error(`Session exchange failed: ${detail}`);
    }
    const session: StoredSession = await res.json();
    this._session.set(session);
    this.writeStorage(session);
  }

  private readStorage(): StoredSession | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as StoredSession) : null;
    } catch {
      return null;
    }
  }

  private writeStorage(session: StoredSession): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  }

  private clearSession(): void {
    this._session.set(null);
    localStorage.removeItem(STORAGE_KEY);
    this.confirmation = null;
  }
}
