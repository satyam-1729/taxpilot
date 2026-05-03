import { environment } from '../../../environments/environment';
import type { AuthUser } from './auth.service';

export interface KycPayload {
  name: string;
  dob: string;        // YYYY-MM-DD
  pan: string;
  aadhaar: string;
}

export async function postKyc(token: string, payload: KycPayload): Promise<AuthUser> {
  const res = await fetch(`${environment.apiBaseUrl}/auth/kyc`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || 'KYC request failed');
  }
  return res.json();
}
