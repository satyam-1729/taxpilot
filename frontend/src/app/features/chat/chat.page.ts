import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-chat-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="chat.html" />`
})
export class ChatPage {}
