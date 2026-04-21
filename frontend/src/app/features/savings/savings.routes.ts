import { Routes } from '@angular/router';

export const SAVINGS_ROUTES: Routes = [
  { path: '', loadComponent: () => import('./savings.page').then(m => m.SavingsPage) },
  { path: 'mobile', data: { variant: 'mobile' }, loadComponent: () => import('./savings.page').then(m => m.SavingsPage) }
];
