import { environment } from '../../../environments/environment';

export type Severity = 'error' | 'warning' | 'info';

export interface FindingSource {
  label: string;
  amount: number | null;
}

export interface Finding {
  severity: Severity;
  code: string;
  fact: string;
  source_a: FindingSource;
  source_b: FindingSource;
  delta: number | null;
  suggestion: string;
}

export interface ReconcileResponse {
  fy: string;
  doc_counts: { form16: number; capital_gains: number; ais: number };
  findings: Finding[];
  summary: { errors: number; warnings: number; info: number };
}

export async function fetchReconcile(token: string, fy: string): Promise<ReconcileResponse> {
  const url = `${environment.apiBaseUrl}/reconcile?fy=${encodeURIComponent(fy)}`;
  const res = await fetch(url, { headers: { authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText));
  return res.json();
}
