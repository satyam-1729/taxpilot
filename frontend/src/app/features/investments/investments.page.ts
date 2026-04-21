import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-investments-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame [file]="file" />`
})
export class InvestmentsPage {
  file = 'investments.html';
  constructor(route: ActivatedRoute) {
    if (route.snapshot.data['variant'] === 'mobile') this.file = 'investments-mobile.html';
  }
}
