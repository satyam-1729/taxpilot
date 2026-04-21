import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="profile.html" />`
})
export class ProfilePage {}
