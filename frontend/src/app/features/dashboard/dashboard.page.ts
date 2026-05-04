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

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, NgApexchartsModule],
  template: `
    <main class="max-w-6xl mx-auto px-6 py-10">

      <!-- Header row: greeting + FY dropdown -->
      <header class="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-extrabold text-primary tracking-tight leading-tight">
            {{ greeting() }}, {{ firstName() }}
          </h1>
          @if (selectedFy) {
            <p class="text-on-surface-variant text-base mt-2">
              Here's your tax snapshot for <span class="font-semibold text-primary">FY {{ selectedFy }}</span>.
            </p>
          } @else {
            <p class="text-on-surface-variant text-base mt-2">
              Upload a Form 16 to see your tax dashboard come alive.
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
                (ngModelChange)="onFyChange()"
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
          <div class="w-16 h-16 mx-auto rounded-2xl bg-primary-fixed flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-primary text-3xl">upload_file</span>
          </div>
          <h2 class="font-headline font-bold text-primary text-xl">No Form 16 yet</h2>
          <p class="text-on-surface-variant mt-2 max-w-sm mx-auto">
            Upload your Form 16 in the Documents tab and your tax dashboard will appear here automatically.
            Capital gains and broker P&amp;L statements live on the Investments tab.
          </p>
          <a routerLink="/documents" class="inline-block mt-6 px-6 py-3 rounded-xl bg-primary text-white font-headline font-bold text-sm hover:opacity-95 transition">
            Go to Documents
          </a>
        </div>
      } @else {

        <!-- Summary cards -->
        <section class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Gross salary</div>
            <div class="font-headline font-extrabold text-primary text-2xl">{{ formatINR(agg().grossSalary) }}</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">TDS deducted</div>
            <div class="font-headline font-extrabold text-primary text-2xl">{{ formatINR(agg().totalTds) }}</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">Taxable income</div>
            <div class="font-headline font-extrabold text-primary text-2xl">{{ formatINR(agg().taxableIncome) }}</div>
          </div>
          <div class="bg-surface-container-lowest rounded-2xl p-5 shadow-sm" [class.bg-secondary-container]="refundDelta() > 0" [class.text-on-secondary-container]="refundDelta() > 0">
            <div class="text-[10px] font-bold uppercase tracking-widest mb-1"
                 [class.text-on-surface-variant]="refundDelta() <= 0">
              {{ refundDelta() > 0 ? 'Estimated refund' : 'Tax payable' }}
            </div>
            <div class="font-headline font-extrabold text-2xl"
                 [class.text-primary]="refundDelta() <= 0">
              {{ formatINR(absRefund()) }}
            </div>
          </div>
        </section>

        <!-- Charts row -->
        <section class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <div class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm">
            <h3 class="font-headline font-bold text-primary mb-4">Salary breakdown</h3>
            @if (salaryChart()) {
              <apx-chart
                [series]="salaryChart()!.series"
                [chart]="salaryChart()!.chart"
                [labels]="salaryChart()!.labels"
                [colors]="salaryChart()!.colors"
                [legend]="salaryChart()!.legend"
                [dataLabels]="salaryChart()!.dataLabels"
                [responsive]="salaryChart()!.responsive"
                [tooltip]="salaryChart()!.tooltip"
                [stroke]="salaryChart()!.stroke"
              />
            } @else {
              <p class="text-sm text-on-surface-variant">No salary breakdown in the parsed Form 16.</p>
            }
          </div>

          <div class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm">
            <h3 class="font-headline font-bold text-primary mb-4">TDS by quarter</h3>
            @if (tdsChart()) {
              <apx-chart
                [series]="tdsChart()!.series"
                [chart]="tdsChart()!.chart"
                [xaxis]="tdsChart()!.xaxis"
                [yaxis]="tdsChart()!.yaxis"
                [colors]="tdsChart()!.colors"
                [plotOptions]="tdsChart()!.plotOptions"
                [dataLabels]="tdsChart()!.dataLabels"
                [fill]="tdsChart()!.fill"
                [tooltip]="tdsChart()!.tooltip"
                [legend]="tdsChart()!.legend"
                [stroke]="tdsChart()!.stroke"
              />
            } @else {
              <p class="text-sm text-on-surface-variant">No TDS quarter data in the parsed Form 16.</p>
            }
          </div>
        </section>

        <!-- Deductions chart -->
        <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-8">
          <h3 class="font-headline font-bold text-primary mb-4">Chapter VI-A deductions claimed</h3>
          @if (deductionsChart()) {
            <apx-chart
              [series]="deductionsChart()!.series"
              [chart]="deductionsChart()!.chart"
              [xaxis]="deductionsChart()!.xaxis"
              [yaxis]="deductionsChart()!.yaxis"
              [colors]="deductionsChart()!.colors"
              [plotOptions]="deductionsChart()!.plotOptions"
              [dataLabels]="deductionsChart()!.dataLabels"
              [fill]="deductionsChart()!.fill"
              [tooltip]="deductionsChart()!.tooltip"
              [legend]="deductionsChart()!.legend"
              [stroke]="deductionsChart()!.stroke"
            />
          } @else {
            <p class="text-sm text-on-surface-variant">No deductions found in the parsed Form 16.</p>
          }
        </section>

        <!-- Source documents for the selected FY -->
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
                @if (doc.employer_name) {
                  <span class="text-xs text-on-surface-variant truncate">{{ doc.employer_name }}</span>
                }
                <span class="text-xs text-on-surface-variant">{{ formatINR(doc.gross_salary) }}</span>
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
export class DashboardPage implements OnInit {
  private readonly auth = inject(AuthService);

  readonly user = computed(() => this.auth.user());
  readonly loading = signal(true);
  readonly docs = signal<DocumentRow[]>([]);

  readonly firstName = computed(() => {
    const u = this.user();
    if (u?.name?.trim()) return u.name.trim().split(/\s+/)[0];
    if (u?.email) return u.email.split('@')[0];
    return 'there';
  });

  selectedFy = '';

  /** Dashboard scope: Form 16 documents only. Capital gains live on /investments. */
  readonly form16Docs = computed(() =>
    this.docs().filter(d => d.doc_type === 'form16' && d.status === 'parsed'),
  );

  readonly availableFys = computed(() => {
    const fys = new Set<string>();
    for (const d of this.form16Docs()) {
      if (!d.ay) continue;
      const fy = (d.parsed_json?.fy as string) || ayToFy(d.ay);
      if (fy) fys.add(fy);
    }
    return Array.from(fys).sort().reverse();
  });

  readonly sourceDocs = computed(() =>
    this.form16Docs().filter(d => this.fyOf(d) === this.selectedFy),
  );

  readonly agg = computed(() => {
    const sources = this.sourceDocs();
    let grossSalary = 0;
    let totalTds = 0;
    let taxableIncome = 0;
    let taxPayable = 0;
    for (const d of sources) {
      grossSalary += Number(d.gross_salary ?? 0);
      totalTds += Number(d.total_tds ?? 0);
      taxableIncome += Number(d.taxable_income ?? 0);
      taxPayable += Number(d.tax_payable ?? 0);
    }
    return { grossSalary, totalTds, taxableIncome, taxPayable };
  });

  readonly refundDelta = computed(() => this.agg().totalTds - this.agg().taxPayable);
  readonly absRefund = computed(() => Math.abs(this.refundDelta()));

  // ── Charts ───────────────────────────────────────────────────────────────

  readonly salaryChart = computed<DonutOptions | null>(() => {
    const components = this.aggregateLineItems('salary.components');
    if (components.size === 0) return null;
    const labels = Array.from(components.keys());
    const series = Array.from(components.values());
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

  readonly tdsChart = computed<BarOptions | null>(() => {
    const quarters = this.aggregateQuarters();
    if (quarters.every(q => q === 0)) return null;
    return {
      series: [{ name: 'TDS', data: quarters }],
      chart: { type: 'bar', height: 300, fontFamily: 'Manrope, sans-serif', toolbar: { show: false } },
      xaxis: {
        categories: ['Q1', 'Q2', 'Q3', 'Q4'],
        labels: { style: { colors: '#454652', fontSize: '12px', fontWeight: 700 } },
        axisBorder: { show: false },
        axisTicks: { show: false },
      },
      yaxis: {
        labels: {
          style: { colors: '#454652', fontSize: '11px' },
          formatter: (v: number) => compactINR(v),
        },
      },
      colors: [TDS_BAR_COLOR],
      plotOptions: { bar: { borderRadius: 10, columnWidth: '50%' } },
      dataLabels: { enabled: false },
      fill: { type: 'solid', opacity: 1 },
      tooltip: { y: { formatter: (v: number) => formatINRStatic(v) } },
      legend: { show: false },
      stroke: { show: false } as ApexStroke,
    };
  });

  readonly deductionsChart = computed<BarOptions | null>(() => {
    const items = this.aggregateLineItems('chapter_vi_a');
    if (items.size === 0) return null;
    const labels = Array.from(items.keys());
    const data = Array.from(items.values());
    return {
      series: [{ name: 'Claimed', data }],
      chart: {
        type: 'bar',
        height: Math.max(220, 60 + labels.length * 48),
        fontFamily: 'Manrope, sans-serif',
        toolbar: { show: false },
      },
      xaxis: {
        categories: labels,
        labels: {
          style: { colors: '#454652', fontSize: '11px' },
          formatter: (v: string) => compactINR(Number(v)),
        },
        axisBorder: { show: false },
        axisTicks: { show: false },
      },
      yaxis: { labels: { style: { colors: '#1a1c1d', fontSize: '12px', fontWeight: 600 } } },
      colors: CHART_PALETTE,
      plotOptions: { bar: { borderRadius: 8, horizontal: true, barHeight: '64%', distributed: true } },
      dataLabels: {
        enabled: true,
        formatter: (v: number) => formatINRStatic(v),
        style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
        offsetX: 0,
      },
      fill: { type: 'solid', opacity: 1 },
      tooltip: { y: { formatter: (v: number) => formatINRStatic(v) } },
      legend: { show: false },
      stroke: { show: false } as ApexStroke,
    } as BarOptions;
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
      if (!this.selectedFy && fys.length > 0) {
        this.selectedFy = fys[0]; // default to most recent FY
      }
    } finally {
      this.loading.set(false);
    }
  }

  onFyChange(): void {
    // Computeds re-run automatically; nothing more needed.
  }

  greeting(): string {
    const h = new Date().getHours();
    if (h < 5) return 'Working late';
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  formatINR(value: number | string | null | undefined): string {
    return formatINRStatic(value);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  private fyOf(d: DocumentRow): string {
    return (d.parsed_json?.fy as string) || ayToFy(d.ay) || '';
  }

  /** Sums {label → amount} across all source docs from a parsed_json path like 'salary.components'. */
  private aggregateLineItems(path: 'salary.components' | 'chapter_vi_a'): Map<string, number> {
    const map = new Map<string, number>();
    for (const d of this.sourceDocs()) {
      const items = path === 'salary.components'
        ? d.parsed_json?.salary?.components
        : d.parsed_json?.chapter_vi_a;
      if (!Array.isArray(items)) continue;
      for (const it of items) {
        const key = it.section ? `${it.section} · ${it.label || ''}`.trim().replace(/·\s*$/, '').trim() : (it.label || 'Other');
        const amt = Number(it.amount ?? 0);
        if (!Number.isFinite(amt) || amt <= 0) continue;
        map.set(key, (map.get(key) ?? 0) + amt);
      }
    }
    return map;
  }

  private aggregateQuarters(): number[] {
    const totals = [0, 0, 0, 0];
    for (const d of this.sourceDocs()) {
      const qs = d.parsed_json?.tds?.quarters;
      if (!Array.isArray(qs)) continue;
      for (const q of qs) {
        const idx = Number(q.quarter) - 1;
        if (idx < 0 || idx > 3) continue;
        totals[idx] += Number(q.tds_deducted ?? 0);
      }
    }
    return totals;
  }
}

// ── Module-level utilities ─────────────────────────────────────────────────

function ayToFy(ay: string | null): string {
  // AY 2026-27 → FY 2025-26 (FY = AY - 1)
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
  if (!Number.isFinite(n) || n === 0) return n === 0 ? '₹0' : '—';
  return INR.format(n);
}

/** Compact INR for axis labels: ₹1.5L, ₹12.3K, etc. */
function compactINR(value: number | null | undefined): string {
  if (value == null) return '—';
  const n = Math.abs(Number(value));
  if (!Number.isFinite(n)) return '—';
  if (n >= 1e7) return `₹${(value / 1e7).toFixed(1)}Cr`;
  if (n >= 1e5) return `₹${(value / 1e5).toFixed(1)}L`;
  if (n >= 1e3) return `₹${(value / 1e3).toFixed(1)}K`;
  return `₹${value}`;
}

/** High-contrast palette for donut + horizontal-bar (each segment a distinct hue). */
const CHART_PALETTE = [
  '#000666', // brand navy
  '#1b6d24', // brand green
  '#f59e0b', // amber
  '#06b6d4', // cyan
  '#ec4899', // pink
  '#8b5cf6', // purple
  '#ef4444', // red
  '#14b8a6', // teal
  '#f97316', // orange
  '#64748b', // slate
];

/** Single uniform color for the TDS-by-quarter bars. Cyan — distinct from brand navy. */
const TDS_BAR_COLOR = '#310B87';
