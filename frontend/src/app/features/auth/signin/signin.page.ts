import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-signin-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="signin.html" />`
})
export class SigninPage {}
