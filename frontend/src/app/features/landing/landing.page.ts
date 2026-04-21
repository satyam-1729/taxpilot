import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-landing-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="landing.html" />`
})
export class LandingPage {}
