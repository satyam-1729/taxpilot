import { environment } from '../../../environments/environment';
import type { AuthUser } from './auth.service';

export async function postKyc(token: string, pan: string, aadhaar: string): Promise<AuthUser> {
  const res = await fetch(`${environment.apiBaseUrl}/auth/kyc`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ pan, aadhaar }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || 'KYC request failed');
  }
  return res.json();
}
