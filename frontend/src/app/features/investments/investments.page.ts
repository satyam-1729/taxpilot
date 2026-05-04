import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  ApexAxisChartSeries,
  ApexChart,
  ApexDataLabels,
  ApexFill,
  ApexLegend,
  ApexNonAxisChartSeries,
  ApexPlotOptions,
  ApexResponsive,
  ApexStroke,
  ApexTooltip,
  ApexXAxis,
  ApexYAxis,
  NgApexchartsModule,
} from 'ng-apexcharts';

import { AuthService } from '../../core/auth/auth.service';
import { DocumentRow, listDocuments } from '../../core/documents/documents.api';

interface DonutOptions {
  series: ApexNonAxisChartSeries;
  chart: ApexChart;
  labels: string[];
  colors: string[];
  legend: ApexLegend;
  dataLabels: ApexDataLabels;
  responsive: ApexResponsive[];
  tooltip: ApexTooltip;
  stroke: ApexStroke;
}

interface BarOptions {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  yaxis: ApexYAxis;
  colors: string[];
  plotOptions: ApexPlotOptions;
  dataLabels: ApexDataLabels;
  fill: ApexFill;
  tooltip: ApexTooltip;
  legend: ApexLegend;
  stroke: ApexStroke;
}

// Capital gains tax rates (post Jul 2024 Budget changes — applies AY 2025-26 onward)
const STCG_111A_RATE = 0.20;        // listed equity short-term
const LTCG_112A_RATE = 0.125;       // listed equity long-term
const LTCG_112A_EXEMPT = 125000;    // first ₹1.25L exempt

@Component({
  selector: 'app-investments-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, NgApexchartsModule],
  template: `
    <main class="max-w-6xl mx-auto px-6 py-10">

      <!-- Header -->
      <header class="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-extrabold text-primary tracking-tight leading-tight">
            Investments
          </h1>
          @if (selectedFy) {
            <p class="text-on-surface-variant text-base mt-2">
              Capital gains, dividends, and tax-exempt income for
              <span class="font-semibold text-primary">FY {{ selectedFy }}</span>.
            </p>
          } @else {
            <p class="text-on-surface-variant text-base mt-2">
              Upload your broker P&L (Zerodha, Groww, Upstox…) or CAMS CAS to see this come alive.
            </p>
          }
        </div>

        <div class="flex items-center gap-3">
          @if (availableFys().length > 0) {
            <label class="flex items-center gap-2 bg-surface-container-lowest rounded-xl pl-4 pr-2 py-2 shadow-sm">
              <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Fiscal year</span>
              <select
                class="bg-transparent border-0 outline-none text-primary font-headline font-bold text-sm pr-1 cursor-pointer"
                [(ngModel)]="selectedFy"
              >
                @for (fy of availableFys(); track fy) {
                  <option [value]="fy">FY {{ fy }}</option>
                }
              </select>
            </label>
          }
        </div>
      </header>

      @if (loading()) {
        <div class="bg-surface-container-low rounded-2xl p-12 text-center text-on-surface-variant">
          Loading…
        </div>
      } @else if (availableFys().length === 0) {
        <div class="bg-surface-container-lowest rounded-3xl p-12 text-center shadow-sm">
          <div class="w-16 h-16 mx-auto rounded-2xl bg-tertiary-fixed flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-on-tertiary-fixed-variant text-3xl">trending_up</span>
          </div>
          <h2 class="font-headline font-bold text-primary text-xl">No capital gains data yet</h2>
          <p class="text-on-surface-variant mt-2 max-w-md mx-auto">
            Upload a tax P&amp;L from your broker (Zerodha, Groww, Upstox, Angel One, etc. — XLSX)
            or your CAMS / KFinTech mutual fund CAS (PDF) on the Documents tab.
          </p>
          <a routerLink="/documents" class="inline-block mt-6 px-6 py-3 rounded-xl bg-primary text-white font-headline font-bold text-sm hover:opacity-95 transition">
            Go to Documents
          </a>
        </div>
      } @else {

        <!-- Total invested hero card -->
        <section class="bg-primary text-white rounded-3xl p-6 shadow-lg shadow-primary/10 mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div class="text-[10px] font-bold uppercase tracking-widest text-white/70 mb-1">Total invested</div>
            <div class="font-headline font-extrabold text-3xl md:text-4xl">{{ formatINR(totalInvested()) }}</div>
            <div class="text-[11px] text-white/70 mt-1">Sum of buy values across all trades and open positions</div>
          </div>
          <div class="text-right">
            <div class="text-[10px] font-bold uppercase tracking-widest text-white/70 mb-1">Realized return</div>
            <div class="font-headline font-extrabold text-2xl"
                 [class.text-secondary-container]="realizedReturn() >= 0"
                 [class.text-error-container]="realizedReturn() < 0">
              {{ formatINR(realizedReturn()) }}
            </div>
            <div class="text-[11px] text-white/70 mt-1">STCG + LTCG (gains − losses)</div>
          </div>
        </section>

        <!-- Summary cards -->
        <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">STCG total</div>
            <div class="font-headline font-extrabold text-2xl"
                 [class.text-primary]="totalStcg() >= 0"
                 [class.text-error]="totalStcg() < 0">
              {{ formatINR(totalStcg()) }}
            </div>
            <div class="text-[11px] text-on-surface-variant mt-1">Equity + non-equity</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">LTCG total</div>
            <div class="font-headline font-extrabold text-2xl"
                 [class.text-primary]="totalLtcg() >= 0"
                 [class.text-error]="totalLtcg() < 0">
              {{ formatINR(totalLtcg()) }}
            </div>
            <div class="text-[11px] text-on-surface-variant mt-1">Equity + non-equity</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Dividends</div>
            <div class="font-headline font-extrabold text-primary text-2xl">{{ formatINR(totalDividends()) }}</div>
            <div class="text-[11px] text-on-surface-variant mt-1">Taxed at slab rate</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm bg-secondary-container/40">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Tax-free income</div>
            <div class="font-headline font-extrabold text-secondary text-2xl">{{ formatINR(totalExempt()) }}</div>
            <div class="text-[11px] text-on-surface-variant mt-1">PPF, EPF, 10(15) etc.</div>
          </div>
        </section>

        <!-- Estimated CG tax -->
        <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-8">
          <h3 class="font-headline font-bold text-primary mb-4 flex items-center gap-2">
            Estimated capital gains tax
            <span class="text-[10px] font-medium text-on-surface-variant uppercase tracking-widest">FY {{ selectedFy }}</span>
          </h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div class="bg-surface-container-low rounded-xl p-4">
              <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">STCG &#64;111A (equity)</div>
              <div class="font-headline font-bold text-primary text-lg">{{ formatINR(stcg111aTax()) }}</div>
              <div class="text-[11px] text-on-surface-variant mt-1">{{ formatINR(agg().stcg111a) }} × 20%</div>
            </div>
            <div class="bg-surface-container-low rounded-xl p-4">
              <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">LTCG &#64;112A (equity)</div>
              <div class="font-headline font-bold text-primary text-lg">{{ formatINR(ltcg112aTax()) }}</div>
              <div class="text-[11px] text-on-surface-variant mt-1">
                ({{ formatINR(agg().ltcg112a) }} − {{ formatINR(LTCG_EXEMPT) }} exempt) × 12.5%
              </div>
            </div>
            <div class="bg-surface-container-low rounded-xl p-4">
              <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Non-equity (slab)</div>
              <div class="font-headline font-bold text-on-surface-variant text-lg">—</div>
              <div class="text-[11px] text-on-surface-variant mt-1">
                {{ formatINR(agg().stcgNonEquity + agg().ltcgNonEquity) }} taxed at your slab rate
              </div>
            </div>
          </div>
          <p class="text-[11px] text-on-surface-variant mt-4 leading-relaxed">
            Rates per Budget 2024 (effective AY 2025-26 onwards). LTCG &#64;112A: first ₹1.25 L exempt; balance &#64;12.5%
            without indexation. Non-equity capital gains taxed at your slab rate; computed once your salary slab is known.
          </p>
        </section>

        <!-- Charts row -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <div class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm">
            <h3 class="font-headline font-bold text-primary mb-4">Capital gains breakdown</h3>
            @if (cgBreakdownChart()) {
              <apx-chart
                [series]="cgBreakdownChart()!.series"
                [chart]="cgBreakdownChart()!.chart"
                [xaxis]="cgBreakdownChart()!.xaxis"
                [yaxis]="cgBreakdownChart()!.yaxis"
                [colors]="cgBreakdownChart()!.colors"
                [plotOptions]="cgBreakdownChart()!.plotOptions"
                [dataLabels]="cgBreakdownChart()!.dataLabels"
                [fill]="cgBreakdownChart()!.fill"
                [tooltip]="cgBreakdownChart()!.tooltip"
                [legend]="cgBreakdownChart()!.legend"
                [stroke]="cgBreakdownChart()!.stroke"
              />
            } @else {
              <p class="text-sm text-on-surface-variant">No capital gains data for this FY.</p>
            }
          </div>

          <div class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm">
            <h3 class="font-headline font-bold text-primary mb-4">Source breakdown</h3>
            @if (sourceChart()) {
              <apx-chart
                [series]="sourceChart()!.series"
                [chart]="sourceChart()!.chart"
                [labels]="sourceChart()!.labels"
                [colors]="sourceChart()!.colors"
                [legend]="sourceChart()!.legend"
                [dataLabels]="sourceChart()!.dataLabels"
                [responsive]="sourceChart()!.responsive"
                [tooltip]="sourceChart()!.tooltip"
                [stroke]="sourceChart()!.stroke"
              />
            } @else {
              <p class="text-sm text-on-surface-variant">Upload statements from multiple brokers to see this breakdown.</p>
            }
          </div>
        </section>

        <!-- Exempt income breakdown -->
        @if (exemptItems().length > 0) {
          <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-8">
            <h3 class="font-headline font-bold text-primary mb-4">Tax-exempt income</h3>
            <ul class="divide-y divide-outline-variant/15">
              @for (item of exemptItems(); track $index) {
                <li class="flex items-center justify-between py-3">
                  <div class="flex items-center gap-3">
                    @if (item.section) {
                      <span class="text-[10px] font-bold uppercase tracking-widest text-on-secondary-container bg-secondary-container px-2 py-0.5 rounded-full">
                        {{ item.section }}
                      </span>
                    }
                    <span class="font-headline font-semibold text-primary">{{ item.label }}</span>
                  </div>
                  <span class="font-headline font-bold text-secondary">{{ formatINR(item.amount) }}</span>
                </li>
              }
            </ul>
          </section>
        }

        <!-- Source documents -->
        <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between gap-4 mb-4 flex-wrap">
            <h3 class="font-headline font-bold text-primary">Source documents</h3>
            <a routerLink="/documents" class="text-sm text-primary font-semibold hover:underline">
              View all →
            </a>
          </div>
          <ul class="space-y-2">
            @for (doc of sourceDocs(); track doc.id) {
              <li class="flex items-center gap-3 py-2 border-b border-outline-variant/15 last:border-0">
                <span class="material-symbols-outlined text-secondary" style="font-variation-settings:'FILL' 1;">check_circle</span>
                <span class="font-headline font-semibold text-primary truncate flex-1">{{ doc.file_name }}</span>
                @if (doc.broker) {
                  <span class="text-xs text-on-surface-variant truncate capitalize">{{ doc.broker }}</span>
                }
                <span class="text-xs text-on-surface-variant">
                  STCG {{ formatINR(doc.stcg_111a) }} · LTCG {{ formatINR(doc.ltcg_112a) }}
                </span>
              </li>
            }
          </ul>
        </section>
      }
    </main>
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
    select { font-family: 'Manrope', sans-serif; }
  `],
})
export class InvestmentsPage implements OnInit {
  private readonly auth = inject(AuthService);

  readonly LTCG_EXEMPT = LTCG_112A_EXEMPT;

  readonly loading = signal(true);
  readonly docs = signal<DocumentRow[]>([]);

  selectedFy = '';

  /** Investments scope: capital_gains documents only. Form 16 lives on /dashboard. */
  readonly cgDocs = computed(() =>
    this.docs().filter(d => d.doc_type === 'capital_gains' && d.status === 'parsed'),
  );

  readonly availableFys = computed(() => {
    const fys = new Set<string>();
    for (const d of this.cgDocs()) {
      const fy = (d.parsed_json?.fy as string) || (d.fy ?? '') || ayToFy(d.ay);
      if (fy) fys.add(fy);
    }
    return Array.from(fys).sort().reverse();
  });

  readonly sourceDocs = computed(() =>
    this.cgDocs().filter(d => this.fyOf(d) === this.selectedFy),
  );

  readonly agg = computed(() => {
    const sources = this.sourceDocs();
    let stcg111a = 0;
    let stcgNonEquity = 0;
    let ltcg112a = 0;
    let ltcgNonEquity = 0;
    let dividends = 0;
    let exempt = 0;
    let invested = 0;
    for (const d of sources) {
      stcg111a += Number(d.stcg_111a ?? 0);
      stcgNonEquity += Number(d.stcg_non_equity ?? 0);
      ltcg112a += Number(d.ltcg_112a ?? 0);
      ltcgNonEquity += Number(d.ltcg_non_equity ?? 0);
      dividends += Number(d.dividends_total ?? 0);
      exempt += Number(d.exempt_income_total ?? 0);
      invested += Number(d.total_invested ?? 0);
    }
    return { stcg111a, stcgNonEquity, ltcg112a, ltcgNonEquity, dividends, exempt, invested };
  });

  readonly totalStcg = computed(() => this.agg().stcg111a + this.agg().stcgNonEquity);
  readonly totalLtcg = computed(() => this.agg().ltcg112a + this.agg().ltcgNonEquity);
  readonly totalDividends = computed(() => this.agg().dividends);
  readonly totalExempt = computed(() => this.agg().exempt);
  readonly totalInvested = computed(() => this.agg().invested);
  readonly realizedReturn = computed(() => this.totalStcg() + this.totalLtcg());

  readonly stcg111aTax = computed(() => Math.max(0, this.agg().stcg111a) * STCG_111A_RATE);
  readonly ltcg112aTax = computed(() =>
    Math.max(0, this.agg().ltcg112a - LTCG_112A_EXEMPT) * LTCG_112A_RATE,
  );

  /** All exempt-income items aggregated across source docs, deduped by (section, label). */
  readonly exemptItems = computed(() => {
    const map = new Map<string, { section: string | null; label: string; amount: number }>();
    for (const d of this.sourceDocs()) {
      const items = d.parsed_json?.exempt_income;
      if (!Array.isArray(items)) continue;
      for (const it of items) {
        const section = (it.section || '').trim() || null;
        const label = (it.label || 'Other').trim();
        const amt = Number(it.amount ?? 0);
        if (!Number.isFinite(amt) || amt <= 0) continue;
        const key = `${section ?? ''}|${label}`;
        const existing = map.get(key);
        if (existing) existing.amount += amt;
        else map.set(key, { section, label, amount: amt });
      }
    }
    return Array.from(map.values()).sort((a, b) => b.amount - a.amount);
  });

  // ── Charts ───────────────────────────────────────────────────────────────

  readonly cgBreakdownChart = computed<BarOptions | null>(() => {
    const a = this.agg();
    const total = Math.abs(a.stcg111a) + Math.abs(a.stcgNonEquity) + Math.abs(a.ltcg112a) + Math.abs(a.ltcgNonEquity);
    if (total === 0) return null;
    return {
      series: [
        { name: 'Equity', data: [a.stcg111a, a.ltcg112a] },
        { name: 'Non-equity', data: [a.stcgNonEquity, a.ltcgNonEquity] },
      ],
      chart: {
        type: 'bar',
        height: 300,
        fontFamily: 'Manrope, sans-serif',
        toolbar: { show: false },
        stacked: true,
      },
      xaxis: {
        categories: ['STCG', 'LTCG'],
        labels: { style: { colors: '#454652', fontSize: '12px', fontWeight: 700 } },
        axisBorder: { show: false },
        axisTicks: { show: false },
      },
      yaxis: {
        labels: { style: { colors: '#454652', fontSize: '11px' }, formatter: (v: number) => compactINR(v) },
      },
      colors: ['#000666', '#06b6d4'],
      plotOptions: { bar: { borderRadius: 8, columnWidth: '50%' } },
      dataLabels: { enabled: false },
      fill: { type: 'solid', opacity: 1 },
      tooltip: { y: { formatter: (v: number) => formatINRStatic(v) } },
      legend: { position: 'bottom', fontSize: '12px', labels: { colors: '#454652' } },
      stroke: { show: false } as ApexStroke,
    };
  });

  readonly sourceChart = computed<DonutOptions | null>(() => {
    // Aggregate absolute |STCG + LTCG| per broker / source.
    const map = new Map<string, number>();
    for (const d of this.sourceDocs()) {
      const key = (d.broker || 'Other').trim();
      const total =
        Math.abs(Number(d.stcg_111a ?? 0)) +
        Math.abs(Number(d.stcg_non_equity ?? 0)) +
        Math.abs(Number(d.ltcg_112a ?? 0)) +
        Math.abs(Number(d.ltcg_non_equity ?? 0));
      if (total <= 0) continue;
      map.set(key, (map.get(key) ?? 0) + total);
    }
    if (map.size === 0) return null;
    const labels = Array.from(map.keys()).map(s => s.charAt(0).toUpperCase() + s.slice(1));
    const series = Array.from(map.values());
    return {
      series,
      labels,
      chart: { type: 'donut', height: 300, fontFamily: 'Manrope, sans-serif' },
      colors: CHART_PALETTE,
      legend: {
        position: 'bottom',
        fontSize: '12px',
        fontWeight: 500,
        labels: { colors: '#454652' },
        itemMargin: { horizontal: 10, vertical: 4 },
      },
      dataLabels: { enabled: true, formatter: (v: number) => `${v.toFixed(0)}%`, style: { fontSize: '11px', fontWeight: 700 } },
      stroke: { width: 3, colors: ['#fff'] },
      tooltip: { y: { formatter: (v: number) => formatINRStatic(v) } },
      responsive: [{ breakpoint: 480, options: { chart: { height: 260 }, legend: { fontSize: '11px' } } }],
    };
  });

  // ── Lifecycle ────────────────────────────────────────────────────────────

  async ngOnInit(): Promise<void> {
    await this.refresh();
  }

  async refresh(): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    try {
      const list = await listDocuments(token);
      this.docs.set(list);
      const fys = this.availableFys();
      if (!this.selectedFy && fys.length > 0) this.selectedFy = fys[0];
    } finally {
      this.loading.set(false);
    }
  }

  formatINR(value: number | string | null | undefined): string {
    return formatINRStatic(value);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  private fyOf(d: DocumentRow): string {
    return (d.parsed_json?.fy as string) || (d.fy ?? '') || ayToFy(d.ay) || '';
  }
}

// ── Module-level utilities ─────────────────────────────────────────────────

function ayToFy(ay: string | null): string {
  if (!ay) return '';
  const m = ay.match(/^(\d{4})-(\d{2})$/);
  if (!m) return '';
  const fyStart = Number(m[1]) - 1;
  const fyEndShort = String(Number(m[2]) - 1).padStart(2, '0');
  return `${fyStart}-${fyEndShort}`;
}

const INR = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

function formatINRStatic(value: number | string | null | undefined): string {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  if (n === 0) return '₹0';
  return INR.format(n);
}

function compactINR(value: number | null | undefined): string {
  if (value == null) return '—';
  const n = Math.abs(Number(value));
  if (!Number.isFinite(n)) return '—';
  if (n >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
  if (n >= 1e3) return `₹${(value / 1e3).toFixed(1)}K`;
  return `₹${value}`;
}

const CHART_PALETTE = [
  '#000666', '#1b6d24', '#f59e0b', '#06b6d4', '#ec4899',
  '#8b5cf6', '#ef4444', '#14b8a6', '#f97316', '#64748b',
];
