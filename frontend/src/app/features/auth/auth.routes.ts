import { Routes } from '@angular/router';

export const AUTH_ROUTES: Routes = [
  { path: 'signin', loadComponent: () => import('./signin/signin.page').then(m => m.SigninPage) },
  { path: 'identity', loadComponent: () => import('./identity/identity.page').then(m => m.IdentityPage) }
];
