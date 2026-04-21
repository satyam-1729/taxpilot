import { Component, Input } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-stitch-frame',
  standalone: true,
  template: `<iframe [src]="safeSrc" class="stitch-frame" title="Stitch screen"></iframe>`,
  styles: [`
    :host { display: block; width: 100%; height: 100%; }
    .stitch-frame { width: 100%; height: 100%; min-height: calc(100vh - 64px); border: 0; background: #f9f9fb; }
  `]
})
export class StitchFrameComponent {
  @Input() set file(name: string) {
    this.safeSrc = this.sanitizer.bypassSecurityTrustResourceUrl(`/stitch/${name}`);
  }
  safeSrc: SafeResourceUrl = '';
  constructor(private sanitizer: DomSanitizer) {}
}
