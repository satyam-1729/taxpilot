import { Routes } from '@angular/router';

export const INVESTMENTS_ROUTES: Routes = [
  { path: '', loadComponent: () => import('./investments.page').then(m => m.InvestmentsPage) },
  { path: 'mobile', data: { variant: 'mobile' }, loadComponent: () => import('./investments.page').then(m => m.InvestmentsPage) }
];
