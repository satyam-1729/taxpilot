import { Component, OnInit, computed, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';
import { DocumentRow } from '../../core/documents/documents.api';
import { DocumentsStore } from '../../core/documents/documents.store';
import { FyService, fyOf } from '../../core/fy/fy.service';
import { Severity } from '../../core/reconcile/reconcile.api';
import { ReconcileStore } from '../../core/reconcile/reconcile.store';
import { formatINR as formatINRFn, privacyMode } from '../../core/ui/privacy';

interface LineItem {
  section?: string;
  label: string;
  amount: number;
}

interface RegimeBreakdown {
  regime: 'old' | 'new';
  grossSalary: number;
  exemptions: LineItem[];        // Section 10 (HRA, LTA, etc.)
  section16: LineItem[];         // Standard deduction, professional tax
  chapterVIA: LineItem[];        // 80C/80D/etc.
  totalAllowances: number;
  taxableIncome: number;
  slabTax: number;
  rebate87A: number;
  surcharge: number;
  cess: number;
  netTax: number;
}

type RegimeTag = 'old' | 'new' | 'both';

interface ChecklistItem {
  id: string;
  section: string;
  title: string;
  description: string;
  cap: string;          // e.g., "₹1.5L"
  capValue: number;     // numeric cap for savings calc
  regime: RegimeTag;    // which regime(s) this deduction is allowed under
  detected: boolean;
  detectedAmount: number;
  headroom: number;     // capValue - detectedAmount
  potentialSavings: number;
}

@Component({
  selector: 'app-savings-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="max-w-6xl mx-auto px-6 py-10">

      <!-- Header -->
      <header class="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <span class="inline-flex items-center px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container text-[10px] font-bold uppercase tracking-widest mb-3">
            Optimization Engine
          </span>
          <h1 class="font-display text-3xl md:text-4xl font-extrabold text-primary tracking-tight leading-tight">
            Regime Intelligence
          </h1>
          @if (selectedFy()) {
            <p class="text-on-surface-variant text-base mt-2 max-w-xl">
              Old vs New regime, computed on your parsed Form 16 for
              <span class="font-semibold text-primary">FY {{ selectedFy() }}</span>.
            </p>
          } @else {
            <p class="text-on-surface-variant text-base mt-2 max-w-xl">
              Upload a Form 16 in the Documents tab to unlock the regime calculator.
            </p>
          }
        </div>
      </header>

      @if (loading()) {
        <!-- Skeleton mirrors the real layout so there's no jarring jump on data arrival. -->
        <section class="bg-primary/10 rounded-2xl h-28 mb-6 sk-shimmer"></section>
        <section class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <article class="bg-surface-container-lowest rounded-2xl h-72 sk-shimmer"></article>
          <article class="bg-surface-container-lowest rounded-2xl h-72 sk-shimmer"></article>
        </section>
        <section class="bg-surface-container-lowest rounded-2xl h-44 mb-6 sk-shimmer"></section>
        <section class="bg-surface-container-lowest rounded-2xl h-96 sk-shimmer"></section>
      } @else if (availableFys().length === 0) {
        <div class="bg-surface-container-lowest rounded-3xl p-12 text-center shadow-sm">
          <div class="w-16 h-16 mx-auto rounded-2xl bg-primary-fixed flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-primary text-3xl">calculate</span>
          </div>
          <h2 class="font-headline font-bold text-primary text-xl">No Form 16 yet</h2>
          <p class="text-on-surface-variant mt-2 max-w-sm mx-auto">
            Upload a Form 16 and we'll compute Old vs New regime side-by-side and recommend the cheaper one.
          </p>
          <a routerLink="/documents" class="inline-block mt-6 px-6 py-3 rounded-xl bg-primary text-white font-headline font-bold text-sm hover:opacity-95 transition">
            Go to Documents
          </a>
        </div>
      } @else {

        <!-- Recommendation banner — only shown when Form 16 exists for the selected FY -->
        @if (sourceDocs().length > 0) {
          <section class="bg-primary rounded-2xl p-6 shadow-sm mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 items-center text-white">
            <div class="md:col-span-2">
              <p class="text-[10px] font-bold uppercase tracking-widest text-primary-fixed-dim mb-1">Our recommendation</p>
              <h2 class="font-headline font-extrabold text-white text-2xl md:text-3xl">
                {{ recommendation().headline }}
              </h2>
              <p class="text-primary-fixed/90 text-sm mt-2 leading-relaxed">
                {{ recommendation().rationale }}
              </p>
            </div>
            <div class="md:text-right">
              <p class="text-[10px] font-bold uppercase tracking-widest text-primary-fixed-dim mb-1">
                {{ recommendation().savingsLabel }}
              </p>
              <p class="font-headline font-extrabold text-secondary-fixed text-3xl">
                {{ formatINR(recommendation().savings) }}
              </p>
            </div>
          </section>
        }

        <!-- Cross-checks vs AIS -->
        @if (reconcileLoading() && findings().length === 0) {
          <section class="bg-surface-container-lowest rounded-2xl h-32 mb-6 sk-shimmer"></section>
        } @else if (findings().length > 0) {
          <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-6">
            <header class="flex items-center justify-between gap-3 mb-4 flex-wrap">
              <div>
                <h3 class="font-headline font-bold text-primary">Cross-checks vs AIS</h3>
                <p class="text-on-surface-variant text-sm mt-1">
                  How your uploaded documents line up with what the IT Department has on file.
                </p>
              </div>
              <div class="flex items-center gap-2 text-xs">
                @if (reconcileLoading()) {
                  <span class="inline-flex items-center gap-1 text-on-surface-variant text-[11px] uppercase tracking-widest">
                    <span class="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                    Refreshing
                  </span>
                }
                @if (reconcileSummary().errors > 0) {
                  <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-error-container/40 text-on-error-container font-bold uppercase tracking-widest">
                    <span class="material-symbols-outlined text-sm" style="font-variation-settings:'FILL' 1;">error</span>
                    {{ reconcileSummary().errors }} action{{ reconcileSummary().errors === 1 ? '' : 's' }}
                  </span>
                }
                @if (reconcileSummary().warnings > 0) {
                  <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-tertiary-container/30 text-tertiary-container font-bold uppercase tracking-widest">
                    <span class="material-symbols-outlined text-sm" style="font-variation-settings:'FILL' 1;">warning</span>
                    {{ reconcileSummary().warnings }} warning{{ reconcileSummary().warnings === 1 ? '' : 's' }}
                  </span>
                }
                @if (aisDocCount() === 0) {
                  <a routerLink="/documents" class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-primary text-white font-bold uppercase tracking-widest text-[10px] hover:opacity-95 transition">
                    <span class="material-symbols-outlined text-sm">upload</span>
                    Upload AIS
                  </a>
                }
              </div>
            </header>

            <ul class="space-y-2">
              @for (f of findings(); track f.code + f.fact) {
                <li
                  class="rounded-xl px-4 py-3 flex items-start gap-3"
                  [ngClass]="severityClasses(f.severity)"
                >
                  <span
                    class="material-symbols-outlined mt-0.5 text-xl"
                    style="font-variation-settings:'FILL' 1;"
                  >
                    {{ severityIcon(f.severity) }}
                  </span>
                  <div class="flex-1 min-w-0">
                    <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <span class="font-headline font-bold">{{ f.fact }}</span>
                      <span class="text-[10px] font-bold uppercase tracking-widest opacity-70">
                        {{ severityLabel(f.severity) }}
                      </span>
                      @if (f.delta != null && f.delta !== 0) {
                        <span class="text-xs font-semibold tabular-nums">
                          Δ {{ f.delta > 0 ? '+' : '' }}{{ formatINR(f.delta) }}
                        </span>
                      }
                    </div>
                    <div class="text-xs opacity-80 mt-0.5 tabular-nums">
                      {{ f.source_a.label }}:
                      {{ f.source_a.amount == null ? '—' : formatINR(f.source_a.amount) }}
                      &nbsp;·&nbsp;
                      {{ f.source_b.label }}:
                      {{ f.source_b.amount == null ? '—' : formatINR(f.source_b.amount) }}
                    </div>
                    <p class="text-sm mt-1 leading-relaxed">{{ f.suggestion }}</p>
                  </div>
                </li>
              }
            </ul>
          </section>
        }

        <!-- Side-by-side regime cards -->
        @if (sourceDocs().length === 0) {
          <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-6 flex items-start gap-3">
            <span class="material-symbols-outlined text-primary text-2xl mt-0.5" style="font-variation-settings:'FILL' 1;">info</span>
            <div class="flex-1">
              <p class="font-headline font-bold text-primary">No Form 16 for FY {{ selectedFy() }}</p>
              <p class="text-on-surface-variant text-sm mt-1">
                Cross-checks against AIS still work, but the regime calculator needs a Form 16
                to compute taxable income. Switch to a year with a Form 16, or
                <a routerLink="/documents" class="text-primary font-semibold underline">upload one</a>.
              </p>
            </div>
          </section>
        } @else {
        <section class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          @for (r of [oldRegime(), newRegime()]; track r.regime) {
            <article
              class="rounded-2xl p-6 shadow-sm flex flex-col transition-colors"
              [class.bg-surface-container-lowest]="r.regime !== recommendation().winner"
              [class.ring-2]="r.regime === recommendation().winner"
              [class.ring-primary]="r.regime === recommendation().winner"
              [style.background-color]="r.regime === recommendation().winner ? 'rgba(0, 6, 102, 0.08)' : null"
            >
              <header class="flex items-start justify-between mb-4">
                <div>
                  <h3 class="font-headline font-bold text-primary text-xl">
                    {{ r.regime === 'old' ? 'Old Regime' : 'New Regime' }}
                  </h3>
                  <p class="text-on-surface-variant text-xs uppercase tracking-widest mt-1">
                    {{ r.regime === 'old' ? 'With exemptions' : 'Lower slabs, fewer exemptions' }}
                  </p>
                </div>
                @if (r.regime === recommendation().winner) {
                  <span class="inline-flex items-center gap-1 bg-secondary-container text-on-secondary-container text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-full">
                    <span class="material-symbols-outlined text-sm" style="font-variation-settings:'FILL' 1;">stars</span>
                    Recommended
                  </span>
                }
              </header>

              <div class="space-y-1.5 text-sm border-b border-outline-variant/15 pb-4 mb-4">
                <div class="flex justify-between"><span class="text-on-surface-variant">Gross salary</span><span class="font-medium">{{ formatINR(r.grossSalary) }}</span></div>
                @for (e of r.section16; track e.label) {
                  <div class="flex justify-between"><span class="text-on-surface-variant">− {{ e.label }}</span><span class="font-medium">{{ formatINR(e.amount) }}</span></div>
                }
                @for (e of r.exemptions; track e.label) {
                  <div class="flex justify-between"><span class="text-on-surface-variant">− {{ e.label }}</span><span class="font-medium">{{ formatINR(e.amount) }}</span></div>
                }
                @for (d of r.chapterVIA; track d.label) {
                  <div class="flex justify-between"><span class="text-on-surface-variant">− {{ d.label }}</span><span class="font-medium">{{ formatINR(d.amount) }}</span></div>
                }
                <div class="flex justify-between pt-2 font-headline font-bold text-primary">
                  <span>Taxable income</span><span>{{ formatINR(r.taxableIncome) }}</span>
                </div>
              </div>

              <div class="space-y-1.5 text-sm">
                <div class="flex justify-between"><span class="text-on-surface-variant">Slab tax</span><span>{{ formatINR(r.slabTax) }}</span></div>
                @if (r.rebate87A > 0) {
                  <div class="flex justify-between"><span class="text-on-surface-variant">− Rebate 87A</span><span>{{ formatINR(r.rebate87A) }}</span></div>
                }
                @if (r.surcharge > 0) {
                  <div class="flex justify-between"><span class="text-on-surface-variant">+ Surcharge</span><span>{{ formatINR(r.surcharge) }}</span></div>
                }
                <div class="flex justify-between"><span class="text-on-surface-variant">+ Health &amp; Education cess (4%)</span><span>{{ formatINR(r.cess) }}</span></div>
              </div>

              <div class="mt-auto pt-5 mt-5 border-t border-outline-variant/15">
                <div class="flex items-end justify-between">
                  <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Net tax</span>
                  <span class="font-headline font-extrabold text-primary text-2xl">{{ formatINR(r.netTax) }}</span>
                </div>
              </div>
            </article>
          }
        </section>
        }

        <!-- What we used -->
        <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-6">
          <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h3 class="font-headline font-bold text-primary">Inputs we extracted from your uploads</h3>
            <span class="text-xs text-on-surface-variant">{{ inputsUsed().count }} fields from {{ sourceDocs().length }} document(s)</span>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            @for (chip of inputsUsed().chips; track chip.label) {
              <div class="flex items-center gap-2 bg-surface-container-low rounded-xl px-3 py-2">
                <span class="material-symbols-outlined text-secondary text-base" style="font-variation-settings:'FILL' 1;">check_circle</span>
                <div class="min-w-0 flex-1">
                  <div class="text-on-surface-variant text-[11px] uppercase tracking-widest truncate">{{ chip.label }}</div>
                  <div class="font-headline font-bold text-primary truncate">{{ formatINR(chip.amount) }}</div>
                </div>
              </div>
            }
          </div>
        </section>

        <!-- Missing doc checklist -->
        <section class="bg-surface-container-lowest rounded-2xl p-6 shadow-sm mb-6">
          <div class="flex items-center justify-between mb-1 flex-wrap gap-2">
            <h3 class="font-headline font-bold text-primary">Documents that could reduce your tax</h3>
            <span class="text-xs text-on-surface-variant">
              {{ checklistCovered() }} / {{ checklist().length }} covered
            </span>
          </div>
          <p class="text-on-surface-variant text-sm mb-4">
            Each item below maps to an Old-Regime deduction. Upload supporting proof in the Documents tab and re-run the calculator.
          </p>
          <ul class="space-y-2">
            @for (item of checklist(); track item.id) {
              <li class="flex items-start gap-3 py-3 border-b border-outline-variant/15 last:border-0">
                <span
                  class="material-symbols-outlined mt-0.5"
                  [class.text-secondary]="item.detected"
                  [class.text-outline]="!item.detected"
                  [style.font-variation-settings]="item.detected ? '\\'FILL\\' 1' : '\\'FILL\\' 0'"
                >
                  {{ item.detected ? 'check_circle' : 'radio_button_unchecked' }}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="font-headline font-bold text-primary">{{ item.title }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">{{ item.section }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Cap {{ item.cap }}</span>
                    <span
                      class="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full inline-flex items-center gap-1"
                      [ngClass]="regimePillClasses(item.regime)"
                      [title]="regimeTooltip(item.regime)"
                    >
                      <span class="material-symbols-outlined text-[12px]" style="font-variation-settings:'FILL' 1;">
                        {{ item.regime === 'both' ? 'compare_arrows' : 'flag' }}
                      </span>
                      {{ regimeLabel(item.regime) }}
                    </span>
                  </div>
                  <p class="text-sm text-on-surface-variant mt-0.5">{{ item.description }}</p>
                  @if (item.detected) {
                    <p class="text-xs text-secondary font-semibold mt-1">
                      Detected: {{ formatINR(item.detectedAmount) }}
                      @if (item.headroom > 0) {
                        · {{ formatINR(item.headroom) }} headroom remaining
                      }
                    </p>
                  } @else if (item.potentialSavings > 0) {
                    <p class="text-xs text-primary font-semibold mt-1">
                      Could save up to {{ formatINR(item.potentialSavings) }} at your marginal rate
                    </p>
                  }
                </div>
              </li>
            }
          </ul>
          <div class="mt-5 flex justify-end">
            <a routerLink="/documents" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white font-headline font-bold text-sm hover:opacity-95 transition">
              <span class="material-symbols-outlined text-base">upload</span>
              Upload supporting docs
            </a>
          </div>
        </section>

        <!-- Caveat -->
        <p class="text-xs text-on-surface-variant text-center max-w-2xl mx-auto">
          Estimates use Income Tax slabs for the selected FY. Surcharge thresholds and rebate u/s 87A applied. Senior-citizen / super-senior basic-exemption uplift not yet modeled — file a profile update if you're 60+.
        </p>
      }
    </main>
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 64px); background: #f9f9fb; }
    select { font-family: 'Manrope', sans-serif; }
    .sk-shimmer {
      position: relative; overflow: hidden;
      background: linear-gradient(90deg, rgba(0,6,102,0.04) 0%, rgba(0,6,102,0.08) 50%, rgba(0,6,102,0.04) 100%);
      background-size: 200% 100%;
      animation: sk-shimmer 1.4s ease-in-out infinite;
    }
    @keyframes sk-shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `],
})
export class SavingsPage implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly docsStore = inject(DocumentsStore);
  private readonly reconcileStore = inject(ReconcileStore);

  // Page-level "loading" only covers the very first cold load — once the
  // stores have data, switching tabs back is instant. Subsequent FY changes
  // surface their freshness via reconcileStore.isLoading(fy) for the inline
  // shimmer on the cross-checks section.
  readonly loading = computed(() => !this.docsStore.loaded());

  /** Docs come straight from the shared store — no per-page fetch. */
  readonly docs = this.docsStore.docs;

  // FY selection lives in a global service so the header dropdown drives every
  // page. The page-level computed signals below all reactively re-derive when
  // selectedFy() flips.
  private readonly fy = inject(FyService);
  protected readonly selectedFy = this.fy.selectedFy;
  protected readonly availableFys = this.fy.availableFys;

  // Reconciliation read straight off the shared cache. Switching FYs is
  // instant for any FY we've already fetched; misses fall through to a
  // single API call (deduped across components).
  readonly reconcileLoading = computed(() => {
    const fy = this.selectedFy();
    return fy ? this.reconcileStore.isLoading(fy) : false;
  });

  readonly findings = computed(() => {
    const fy = this.selectedFy();
    if (!fy) return [];
    return this.reconcileStore.byFy(fy)?.findings ?? [];
  });

  readonly reconcileSummary = computed(() => {
    const fy = this.selectedFy();
    return (fy && this.reconcileStore.byFy(fy)?.summary) || { errors: 0, warnings: 0, info: 0 };
  });

  readonly aisDocCount = computed(() => {
    const fy = this.selectedFy();
    return (fy && this.reconcileStore.byFy(fy)?.doc_counts.ais) || 0;
  });

  readonly errorFindings = computed(() => this.findings().filter(f => f.severity === 'error'));
  readonly warningFindings = computed(() => this.findings().filter(f => f.severity === 'warning'));
  readonly infoFindings = computed(() => this.findings().filter(f => f.severity === 'info'));

  readonly form16Docs = computed(() =>
    this.docs().filter(d => d.doc_type === 'form16' && d.status === 'parsed'),
  );

  readonly sourceDocs = computed(() =>
    this.form16Docs().filter(d => fyOf(d) === this.selectedFy()),
  );

  // ── Aggregate raw line items from all source docs for the selected FY ────

  readonly grossSalary = computed(() => {
    let sum = 0;
    for (const d of this.sourceDocs()) sum += Number(d.gross_salary ?? 0);
    return sum;
  });

  /** Section 10 exemptions (HRA, LTA, etc.) — only valid under Old Regime. */
  readonly section10 = computed<LineItem[]>(() =>
    this.aggregate(d => d.parsed_json?.salary?.section_10_exemptions),
  );

  /** Section 16 (standard deduction, professional tax). */
  readonly section16 = computed<LineItem[]>(() =>
    this.aggregate(d => d.parsed_json?.salary?.section_16),
  );

  /** Chapter VI-A (80C/80D/80E/etc.) — only valid under Old Regime. */
  readonly chapterVIA = computed<LineItem[]>(() =>
    this.aggregate(d => d.parsed_json?.chapter_vi_a),
  );

  // ── Regime breakdowns ────────────────────────────────────────────────────

  readonly oldRegime = computed<RegimeBreakdown>(() => {
    privacyMode();
    const fy = this.selectedFy();
    const gross = this.grossSalary();
    const sec16 = this.section16().length
      ? this.section16()
      : [{ label: 'Standard deduction', section: '16(ia)', amount: STD_DED_OLD }];
    const sec10 = this.section10();
    const ch6 = this.chapterVIA();
    const totalAllowances = sumAmounts(sec16) + sumAmounts(sec10) + sumAmounts(ch6);
    const taxable = Math.max(0, gross - totalAllowances);
    return computeBreakdown('old', fy, gross, sec10, sec16, ch6, taxable);
  });

  readonly newRegime = computed<RegimeBreakdown>(() => {
    privacyMode();
    const fy = this.selectedFy();
    const gross = this.grossSalary();
    const stdDed = stdDedNew(fy);
    const sec16: LineItem[] = [{ label: 'Standard deduction', section: '16(ia)', amount: stdDed }];
    // Employer NPS 80CCD(2) is allowed under New Regime — pull from chapter_vi_a if present.
    const employerNps = this.chapterVIA().filter(li => /80CCD\s*\(2\)/i.test(li.section || '') || /employer.*nps/i.test(li.label || ''));
    const allowances = stdDed + sumAmounts(employerNps);
    const taxable = Math.max(0, gross - allowances);
    return computeBreakdown('new', fy, gross, [], sec16, employerNps, taxable);
  });

  readonly recommendation = computed(() => {
    const oldT = this.oldRegime().netTax;
    const newT = this.newRegime().netTax;
    const winner: 'old' | 'new' = oldT <= newT ? 'old' : 'new';
    const savings = Math.abs(oldT - newT);
    if (savings === 0) {
      return {
        winner,
        headline: 'Both regimes are equal for you this year.',
        rationale: 'Your deductions exactly offset the lower New-Regime slabs. Pick whichever is simpler to file.',
        savings: 0,
        savingsLabel: 'No difference',
      };
    }
    if (winner === 'new') {
      return {
        winner,
        headline: 'Pick the New Regime — lower slabs win.',
        rationale: 'Your current deductions don\'t offset the New Regime\'s lower slab rates. Upload more 80C/80D/HRA proofs (see checklist below) to revisit.',
        savings,
        savingsLabel: 'Saves under New',
      };
    }
    return {
      winner,
      headline: 'Stick with the Old Regime — your deductions pay off.',
      rationale: 'Your exemptions and Chapter VI-A deductions outweigh the New Regime\'s lower slab rates.',
      savings,
      savingsLabel: 'Saves under Old',
    };
  });

  // ── "What we extracted" chips ────────────────────────────────────────────

  readonly inputsUsed = computed(() => {
    privacyMode();
    const chips: { label: string; amount: number }[] = [];
    const gross = this.grossSalary();
    if (gross > 0) chips.push({ label: 'Gross salary', amount: gross });
    let totalTds = 0;
    for (const d of this.sourceDocs()) totalTds += Number(d.total_tds ?? 0);
    if (totalTds > 0) chips.push({ label: 'TDS deducted', amount: totalTds });
    for (const li of this.section16()) chips.push({ label: li.label, amount: li.amount });
    for (const li of this.section10()) chips.push({ label: li.label, amount: li.amount });
    for (const li of this.chapterVIA()) chips.push({ label: `${li.section ?? ''} ${li.label}`.trim(), amount: li.amount });
    return { chips, count: chips.length };
  });

  // ── Document / deduction checklist ───────────────────────────────────────

  readonly checklist = computed<ChecklistItem[]>(() => {
    privacyMode();
    const marginal = marginalRateOld(this.oldRegime().taxableIncome);
    const detected = (matcher: (li: LineItem) => boolean): number => {
      let sum = 0;
      for (const li of [...this.chapterVIA(), ...this.section10()]) {
        if (matcher(li)) sum += li.amount;
      }
      return sum;
    };
    // True once the user has uploaded an AIS / TIS / 26AS *for the selected
    // FY* that parsed successfully. The checklist is FY-scoped — an AIS for
    // 2025-26 must not satisfy the 2024-25 row.
    const fy = this.selectedFy();
    const aisDetected = this.docs().some(
      d => d.doc_type === 'ais' && d.status === 'parsed' && fyOf(d) === fy,
    );
    const item = (
      id: string,
      section: string,
      title: string,
      description: string,
      cap: string,
      capValue: number,
      regime: RegimeTag,
      matcher: (li: LineItem) => boolean,
    ): ChecklistItem => {
      const amt = detected(matcher);
      const headroom = Math.max(0, capValue - amt);
      return {
        id,
        section,
        title,
        description,
        cap,
        capValue,
        regime,
        detected: amt > 0,
        detectedAmount: amt,
        headroom,
        potentialSavings: Math.round(headroom * marginal * 1.04),
      };
    };

    return [
      item(
        '80c', '80C',
        'PPF / ELSS / LIC / EPF / NSC / home-loan principal',
        'Sum of long-term savings + life insurance + tuition fees + home-loan principal repayment.',
        '₹1.5L', 150000, 'old',
        li => /80C\b/i.test(li.section ?? '') && !/80CCD/i.test(li.section ?? ''),
      ),
      item(
        '80ccd1b', '80CCD(1B)',
        'NPS Tier-I (additional)',
        'Voluntary NPS contribution over and above 80C — separate ₹50K bucket.',
        '₹50K', 50000, 'old',
        li => /80CCD\s*\(1B\)/i.test(li.section ?? ''),
      ),
      item(
        '80d', '80D',
        'Health insurance premium (self + parents)',
        'Mediclaim premium for self/spouse/kids (₹25K) + parents (₹25K, ₹50K if senior) + ₹5K preventive checkup.',
        '₹1L', 100000, 'old',
        li => /80D\b/i.test(li.section ?? ''),
      ),
      item(
        'hra', '10(13A)',
        'Rent receipts + rent agreement',
        'HRA exemption — needs landlord PAN if annual rent > ₹1L. Old Regime only.',
        'Salary-linked', 0, 'old',
        li => /10\s*\(13A\)/i.test(li.section ?? '') || /\bHRA\b/i.test(li.label ?? ''),
      ),
      item(
        '24b', '24(b)',
        'Home-loan interest certificate',
        'Interest on housing loan — self-occupied capped at ₹2L per year (Old Regime only).',
        '₹2L', 200000, 'old',
        li => /24\s*\(b\)/i.test(li.section ?? '') || /home\s*loan\s*interest/i.test(li.label ?? ''),
      ),
      item(
        '80e', '80E',
        'Education-loan interest certificate',
        'Interest on education loan for self/spouse/children — no upper cap, 8-year window.',
        'Uncapped', 50000, 'old',
        li => /80E\b/i.test(li.section ?? ''),
      ),
      item(
        '80g', '80G',
        'Donation receipts (PM CARES, registered NGOs)',
        '50% or 100% of donation depending on the institution. Receipt must show 80G registration.',
        'Donation-linked', 25000, 'old',
        li => /80G\b/i.test(li.section ?? ''),
      ),
      item(
        '80tta', '80TTA / 80TTB',
        'Savings-bank interest passbook',
        '₹10K cap on SB interest (₹50K for seniors incl. FDs). Mostly auto-fetched from AIS.',
        '₹10K / ₹50K', 10000, 'old',
        li => /80TT[AB]\b/i.test(li.section ?? ''),
      ),
      item(
        '80ccd2', '80CCD(2)',
        'Employer NPS contribution proof',
        'Employer\'s NPS contribution — allowed under both regimes, capped at 14% of basic salary (govt) / 10% (private).',
        '~14% of basic', 200000, 'both',
        li => /80CCD\s*\(2\)/i.test(li.section ?? ''),
      ),
      {
        id: 'ais',
        section: 'AIS / 26AS',
        title: 'AIS / Form 26AS download',
        description: 'Cross-checks TDS, dividends, interest, and high-value transactions reported to the IT Dept.',
        cap: 'Verification',
        capValue: 0,
        regime: 'both',
        detected: aisDetected,
        detectedAmount: 0,
        headroom: 0,
        potentialSavings: 0,
      },
    ];
  });

  readonly checklistCovered = computed(() => this.checklist().filter(c => c.detected).length);

  // ── Lifecycle ────────────────────────────────────────────────────────────

  constructor() {
    // Reactively pull reconciliation findings from the cache whenever the
    // global FY changes. ReconcileStore handles dedup and per-FY caching —
    // a hit returns synchronously, a miss fires one network request.
    effect(() => {
      const fy = this.selectedFy();
      if (!fy) return;
      const token = this.auth.token();
      if (!token) return;
      void this.reconcileStore.ensureFor(token, fy).catch(() => {
        // Reconcile is advisory; swallow failures so the page still renders.
      });
    });
  }

  async ngOnInit(): Promise<void> {
    const token = this.auth.token();
    if (!token) return;
    // Cache hit → returns synchronously, page renders without a flicker.
    // Cache miss → fires one request shared across components.
    const list = await this.docsStore.ensureLoaded(token);
    this.fy.register(list);
  }

  severityIcon(s: Severity): string {
    return { error: 'error', warning: 'warning', info: 'info' }[s];
  }

  severityClasses(s: Severity): string {
    return {
      error: 'bg-error-container/40 text-on-error-container ring-1 ring-error-container',
      warning: 'bg-tertiary-container/30 text-tertiary-container ring-1 ring-tertiary-container/40',
      info: 'bg-surface-container-high text-on-surface-variant ring-1 ring-outline-variant/40',
    }[s];
  }

  severityLabel(s: Severity): string {
    return { error: 'Action needed', warning: 'Heads up', info: 'FYI' }[s];
  }

  protected readonly formatINR = formatINRFn;

  regimeLabel(tag: RegimeTag): string {
    return { old: 'Old regime', new: 'New regime', both: 'Old + New' }[tag];
  }

  regimePillClasses(tag: RegimeTag): string {
    return {
      old: 'bg-primary text-white',
      new: 'bg-secondary-container text-on-secondary-container',
      both: 'bg-surface-container-high text-on-surface-variant ring-1 ring-outline-variant/40',
    }[tag];
  }

  regimeTooltip(tag: RegimeTag): string {
    return {
      old: 'Only deductible if you file under the Old Regime.',
      new: 'Only deductible if you file under the New Regime.',
      both: 'Useful regardless of which regime you pick.',
    }[tag];
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  private aggregate(picker: (d: DocumentRow) => any): LineItem[] {
    const map = new Map<string, LineItem>();
    for (const d of this.sourceDocs()) {
      const items = picker(d);
      if (!Array.isArray(items)) continue;
      for (const it of items) {
        const amt = Number(it.amount ?? 0);
        if (!Number.isFinite(amt) || amt <= 0) continue;
        const key = `${it.section ?? ''}|${it.label ?? 'Other'}`;
        const existing = map.get(key);
        if (existing) existing.amount += amt;
        else map.set(key, { section: it.section, label: it.label || 'Other', amount: amt });
      }
    }
    return Array.from(map.values());
  }
}

// ── Tax-engine constants & helpers (frontend preview only) ─────────────────
// Slabs are FY-keyed. Backend remains the source of truth for filing.

const SLABS_NEW: Record<string, [number, number][]> = {
  '2025-26': [[400000, 0], [800000, 0.05], [1200000, 0.10], [1600000, 0.15], [2000000, 0.20], [2400000, 0.25], [Infinity, 0.30]],
  '2024-25': [[300000, 0], [700000, 0.05], [1000000, 0.10], [1200000, 0.15], [1500000, 0.20], [Infinity, 0.30]],
  '2023-24': [[300000, 0], [600000, 0.05], [900000, 0.10], [1200000, 0.15], [1500000, 0.20], [Infinity, 0.30]],
};

const SLABS_OLD: [number, number][] = [
  [250000, 0], [500000, 0.05], [1000000, 0.20], [Infinity, 0.30],
];

const REBATE_NEW: Record<string, { limit: number; max: number }> = {
  '2025-26': { limit: 1200000, max: 60000 },
  '2024-25': { limit: 700000, max: 25000 },
  '2023-24': { limit: 700000, max: 25000 },
};

const REBATE_OLD = { limit: 500000, max: 12500 };

const STD_DED_NEW_BY_FY: Record<string, number> = {
  '2025-26': 75000, '2024-25': 75000, '2023-24': 50000,
};

const STD_DED_OLD = 50000;

function stdDedNew(fy: string): number {
  return STD_DED_NEW_BY_FY[fy] ?? 75000;
}

function slabsForRegime(regime: 'old' | 'new', fy: string): [number, number][] {
  if (regime === 'old') return SLABS_OLD;
  return SLABS_NEW[fy] ?? SLABS_NEW['2025-26'];
}

function rebateConfig(regime: 'old' | 'new', fy: string): { limit: number; max: number } {
  return regime === 'old' ? REBATE_OLD : (REBATE_NEW[fy] ?? REBATE_NEW['2025-26']);
}

function applySlabs(taxable: number, slabs: [number, number][]): number {
  let tax = 0, lower = 0;
  for (const [upper, rate] of slabs) {
    if (taxable > lower) {
      const slabIncome = Math.min(taxable, upper) - lower;
      tax += slabIncome * rate;
    }
    lower = upper;
    if (taxable <= upper) break;
  }
  return tax;
}

function surchargeOn(tax: number, taxable: number, regime: 'old' | 'new'): number {
  let rate = 0;
  if (taxable > 50000000) rate = regime === 'new' ? 0.25 : 0.37;
  else if (taxable > 20000000) rate = 0.25;
  else if (taxable > 10000000) rate = 0.15;
  else if (taxable > 5000000) rate = 0.10;
  return tax * rate;
}

function computeBreakdown(
  regime: 'old' | 'new',
  fy: string,
  grossSalary: number,
  exemptions: LineItem[],
  section16: LineItem[],
  chapterVIA: LineItem[],
  taxableIncome: number,
): RegimeBreakdown {
  const slabs = slabsForRegime(regime, fy);
  const slabTax = applySlabs(taxableIncome, slabs);
  const reb = rebateConfig(regime, fy);
  const rebate87A = taxableIncome <= reb.limit ? Math.min(slabTax, reb.max) : 0;
  const taxAfterRebate = Math.max(0, slabTax - rebate87A);
  const surcharge = surchargeOn(taxAfterRebate, taxableIncome, regime);
  const cess = (taxAfterRebate + surcharge) * 0.04;
  const netTax = Math.round(taxAfterRebate + surcharge + cess);
  return {
    regime,
    grossSalary,
    exemptions,
    section16,
    chapterVIA,
    totalAllowances: sumAmounts(exemptions) + sumAmounts(section16) + sumAmounts(chapterVIA),
    taxableIncome,
    slabTax: Math.round(slabTax),
    rebate87A: Math.round(rebate87A),
    surcharge: Math.round(surcharge),
    cess: Math.round(cess),
    netTax,
  };
}

function marginalRateOld(taxable: number): number {
  if (taxable <= 250000) return 0;
  if (taxable <= 500000) return 0.05;
  if (taxable <= 1000000) return 0.20;
  return 0.30;
}

function sumAmounts(items: LineItem[]): number {
  return items.reduce((s, it) => s + (Number(it.amount) || 0), 0);
}
