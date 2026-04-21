import { Component } from '@angular/core';
import { StitchFrameComponent } from '../../shared/stitch-frame/stitch-frame.component';

@Component({
  selector: 'app-documents-page',
  standalone: true,
  imports: [StitchFrameComponent],
  template: `<app-stitch-frame file="documents.html" />`
})
export class DocumentsPage {}
