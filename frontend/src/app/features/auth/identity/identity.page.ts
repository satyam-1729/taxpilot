import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-identity-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="identity.html" />`
})
export class IdentityPage {}
