import { Routes } from '@angular/router';

import { authGuard, guestGuard } from '../../core/auth/guards';

export const AUTH_ROUTES: Routes = [
  {
    path: 'signin',
    canActivate: [guestGuard],
    loadComponent: () => import('./signin/signin.page').then(m => m.SigninPage),
  },
  {
    path: 'identity',
    canActivate: [authGuard],
    loadComponent: () => import('./identity/identity.page').then(m => m.IdentityPage),
  },
];
