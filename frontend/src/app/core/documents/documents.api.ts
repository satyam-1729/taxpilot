import { environment } from '../../../environments/environment';

export type DocStatus = 'queued' | 'parsing' | 'parsed' | 'failed' | 'needs_password';
export type DocType = 'form16' | 'capital_gains' | 'unknown';

export interface DocumentRow {
  id: string;
  doc_type: DocType;
  status: DocStatus;
  file_name: string;
  file_size_bytes: number;
  ay: string | null;
  fy: string | null;
  // Form 16 fields
  employer_name: string | null;
  employee_pan: string | null;
  gross_salary: string | null;
  total_tds: string | null;
  taxable_income: string | null;
  tax_payable: string | null;
  regime: string | null;
  // Capital gains fields
  broker: string | null;
  stcg_111a: string | null;
  stcg_non_equity: string | null;
  ltcg_112a: string | null;
  ltcg_non_equity: string | null;
  dividends_total: string | null;
  exempt_income_total: string | null;
  total_invested: string | null;
  // Common
  parsed_json: any | null;
  error: string | null;
  created_at: string;
  parsed_at: string | null;
}

export interface UploadResponse {
  id: string;
  status: DocStatus;
  deduplicated: boolean;
}

function authHeaders(token: string): HeadersInit {
  return { authorization: `Bearer ${token}` };
}

export async function uploadDocument(token: string, file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${environment.apiBaseUrl}/documents/upload`, {
    method: 'POST',
    headers: authHeaders(token),
    body: form,
  });
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      detail = await res.text().catch(() => res.statusText);
    }
    const err = new Error(detail || `Upload failed (${res.status})`);
    (err as any).status = res.status;
    throw err;
  }
  return res.json();
}

export async function listDocuments(token: string): Promise<DocumentRow[]> {
  const res = await fetch(`${environment.apiBaseUrl}/documents`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}

export async function getDocument(token: string, id: string): Promise<DocumentRow> {
  const res = await fetch(`${environment.apiBaseUrl}/documents/${id}`, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}

export async function deleteDocument(token: string, id: string): Promise<void> {
  const res = await fetch(`${environment.apiBaseUrl}/documents/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(await res.text().catch(() => res.statusText));
  }
}

export async function submitPassword(token: string, id: string, password: string): Promise<UploadResponse> {
  const res = await fetch(`${environment.apiBaseUrl}/documents/${id}/decrypt`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'content-type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    } catch {
      detail = await res.text().catch(() => res.statusText);
    }
    const err = new Error(detail || `Decryption failed (${res.status})`);
    (err as any).status = res.status;
    throw err;
  }
  return res.json();
}
