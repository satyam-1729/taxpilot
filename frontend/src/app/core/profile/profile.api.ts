import { environment } from '../../../environments/environment';

export type AccountType = 'savings' | 'current';

export interface BankAccount {
  id: string;
  bank_name: string;
  ifsc: string;
  account_last4: string;
  account_type: AccountType;
  is_primary: boolean;
  created_at: string;
}

export interface BankAccountInput {
  bank_name: string;
  ifsc: string;
  account_number: string;
  account_type: AccountType;
  is_primary?: boolean;
}

function authHeaders(token: string): HeadersInit {
  return { authorization: `Bearer ${token}` };
}

export async function listBankAccounts(token: string): Promise<BankAccount[]> {
  const res = await fetch(`${environment.apiBaseUrl}/profile/bank-accounts`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}

export async function addBankAccount(token: string, input: BankAccountInput): Promise<BankAccount> {
  const res = await fetch(`${environment.apiBaseUrl}/profile/bank-accounts`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'content-type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `Add failed (${res.status})`);
  }
  return res.json();
}

export async function deleteBankAccount(token: string, id: string): Promise<void> {
  const res = await fetch(`${environment.apiBaseUrl}/profile/bank-accounts/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
}

export async function makePrimaryBankAccount(token: string, id: string): Promise<BankAccount> {
  const res = await fetch(`${environment.apiBaseUrl}/profile/bank-accounts/${id}/make-primary`, {
    method: 'PATCH',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}
