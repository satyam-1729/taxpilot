import { environment } from '../../../environments/environment';

export type DocStatus = 'queued' | 'parsing' | 'parsed' | 'failed' | 'needs_password';

export interface DocumentRow {
  id: string;
  doc_type: string;
  status: DocStatus;
  file_name: string;
  file_size_bytes: number;
  ay: string | null;
  employer_name: string | null;
  employee_pan: string | null;
  gross_salary: string | null;
  total_tds: string | null;
  taxable_income: string | null;
  tax_payable: string | null;
  regime: string | null;
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

export async function uploadDocument(token: string, file: File, docType = 'form16'): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${environment.apiBaseUrl}/documents/upload?doc_type=${docType}`, {
    method: 'POST',
    headers: authHeaders(token),
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `Upload failed (${res.status})`);
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

export async function submitPassword(token: string, id: string, password: string): Promise<UploadResponse> {
  const res = await fetch(`${environment.apiBaseUrl}/documents/${id}/decrypt`, {
    method: 'POST',
    headers: { ...authHeaders(token), 'content-type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(detail || `Decryption failed (${res.status})`);
  }
  return res.json();
}
