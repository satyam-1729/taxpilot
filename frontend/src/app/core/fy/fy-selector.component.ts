import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';

import { FyService } from './fy.service';

/**
 * Header-mounted financial-year selector. Custom popup so we can style the
 * option list (a native <select>'s drop-down is OS-painted and won't respect
 * the design system).
 *
 * Keyboard model:
 *   Trigger: Enter / Space / ArrowDown opens the panel.
 *   Panel:   ArrowUp / ArrowDown move the highlight, Enter selects,
 *            Escape closes, Tab closes (focus moves on naturally).
 */
@Component({
  selector: 'app-fy-selector',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (fy.availableFys().length > 0) {
      <div class="fy-root">
        <button
          type="button"
          class="fy-trigger"
          [class.fy-trigger--open]="open()"
          [attr.aria-haspopup]="'listbox'"
          [attr.aria-expanded]="open()"
          (click)="toggle()"
          (keydown)="onTriggerKey($event)"
        >
          <span class="fy-label">FY</span>
          <span class="fy-value">{{ fy.selectedFy() }}</span>
          <svg
            class="fy-chevron"
            [class.fy-chevron--open]="open()"
            viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"
          >
            <path d="M2.5 4.5L6 8l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>

        @if (open()) {
          <div class="fy-panel" role="listbox" tabindex="-1" (keydown)="onPanelKey($event)">
            <div class="fy-panel-head">Financial year</div>
            @for (f of fy.availableFys(); track f; let i = $index) {
              <button
                type="button"
                class="fy-option"
                role="option"
                [class.fy-option--selected]="f === fy.selectedFy()"
                [class.fy-option--focus]="i === focusIndex()"
                [attr.aria-selected]="f === fy.selectedFy()"
                (mouseenter)="focusIndex.set(i)"
                (click)="pick(f)"
              >
                <span class="fy-option-year">FY {{ f }}</span>
                <span class="fy-option-range">{{ rangeFor(f) }}</span>
                @if (f === fy.selectedFy()) {
                  <svg class="fy-check" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                    <path d="M3 8.5l3.5 3.5L13 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                }
              </button>
            }
          </div>
        }
      </div>
    }
  `,
  styles: [`
    .fy-root { position: relative; display: inline-flex; }

    /* ── Trigger ────────────────────────────────────────────────────────── */
    .fy-trigger {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 7px 12px 7px 14px;
      background: #f3f3f5; border: 0; border-radius: 999px;
      cursor: pointer;
      font-family: 'Manrope', sans-serif;
      transition: background 0.15s, box-shadow 0.15s;
    }
    .fy-trigger:hover { background: #e5e5ed; }
    .fy-trigger:focus-visible { outline: 2px solid #000666; outline-offset: 2px; }
    .fy-trigger--open {
      background: #e0e0ff;
      box-shadow: 0 1px 2px rgba(0, 6, 102, 0.08);
    }
    .fy-label {
      font-size: 10px; font-weight: 700;
      color: #454652; letter-spacing: 0.14em; text-transform: uppercase;
    }
    .fy-trigger--open .fy-label { color: #000666; }
    .fy-value {
      font-size: 13px; font-weight: 800; color: #000666;
      letter-spacing: -0.01em;
    }
    .fy-chevron {
      color: #454652;
      transition: transform 0.18s ease, color 0.15s;
    }
    .fy-chevron--open { transform: rotate(180deg); color: #000666; }

    /* ── Panel ─────────────────────────────────────────────────────────── */
    .fy-panel {
      position: absolute; top: calc(100% + 8px); right: 0;
      min-width: 220px;
      background: #ffffff;
      border-radius: 14px;
      box-shadow:
        0 1px 2px rgba(15, 18, 25, 0.06),
        0 12px 32px rgba(15, 18, 25, 0.12);
      padding: 6px;
      z-index: 30;
      animation: fy-pop 0.14s ease-out;
    }
    @keyframes fy-pop {
      from { opacity: 0; transform: translateY(-4px) scale(0.98); }
      to   { opacity: 1; transform: translateY(0)    scale(1); }
    }
    .fy-panel-head {
      padding: 8px 12px 6px;
      font-family: 'Manrope', sans-serif;
      font-size: 10px; font-weight: 700;
      color: #6c6e7a; letter-spacing: 0.14em; text-transform: uppercase;
    }

    /* ── Option ────────────────────────────────────────────────────────── */
    .fy-option {
      width: 100%; display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center; gap: 10px;
      padding: 9px 12px;
      background: transparent; border: 0; border-radius: 10px;
      font-family: 'Manrope', sans-serif; text-align: left; cursor: pointer;
      transition: background 0.12s;
    }
    .fy-option-year {
      font-size: 13px; font-weight: 800;
      color: #1a1c1d; letter-spacing: -0.01em;
    }
    .fy-option-range {
      font-size: 11px; font-weight: 500;
      color: #6c6e7a;
    }
    .fy-check { color: #1b6d24; grid-column: 3; }

    .fy-option--focus { background: #f3f3f5; }
    .fy-option--selected {
      background: #e0e0ff;
    }
    .fy-option--selected .fy-option-year { color: #000666; }
    .fy-option--selected .fy-option-range { color: #000666; opacity: 0.7; }

    .fy-option:focus-visible { outline: 2px solid #000666; outline-offset: -2px; }
  `],
})
export class FySelectorComponent {
  protected readonly fy = inject(FyService);
  private readonly host = inject(ElementRef<HTMLElement>);

  protected readonly open = signal(false);
  protected readonly focusIndex = signal(0);

  protected readonly fys = computed(() => this.fy.availableFys());

  toggle(): void {
    if (this.open()) {
      this.close();
    } else {
      this.openPanel();
    }
  }

  private openPanel(): void {
    const idx = Math.max(0, this.fys().indexOf(this.fy.selectedFy()));
    this.focusIndex.set(idx);
    this.open.set(true);
  }

  private close(): void {
    this.open.set(false);
  }

  pick(f: string): void {
    this.fy.setSelectedFy(f);
    this.close();
  }

  /** Convert FY 2024-25 → "1 Apr 2024 – 31 Mar 2025" — surfaces what the year actually means. */
  rangeFor(fy: string): string {
    const m = fy.match(/^(\d{4})-(\d{2})$/);
    if (!m) return '';
    const start = Number(m[1]);
    const end = Number(m[2]) + 2000;
    return `1 Apr ${start} – 31 Mar ${end}`;
  }

  // ── Keyboard ────────────────────────────────────────────────────────────

  onTriggerKey(e: KeyboardEvent): void {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      this.openPanel();
    }
  }

  onPanelKey(e: KeyboardEvent): void {
    const list = this.fys();
    if (e.key === 'Escape') {
      e.preventDefault();
      this.close();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.focusIndex.set((this.focusIndex() + 1) % list.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.focusIndex.set((this.focusIndex() - 1 + list.length) % list.length);
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      const target = list[this.focusIndex()];
      if (target) this.pick(target);
    } else if (e.key === 'Tab') {
      this.close();
    }
  }

  /** Outside click dismisses. */
  @HostListener('document:click', ['$event'])
  onDocClick(e: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(e.target as Node)) {
      this.close();
    }
  }
}
