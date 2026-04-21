import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame [file]="file" />`
})
export class DashboardPage {
  file = 'dashboard.html';
  constructor(route: ActivatedRoute) {
    if (route.snapshot.data['variant'] === 'mobile') this.file = 'dashboard-mobile.html';
  }
}
