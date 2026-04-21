import { Routes } from '@angular/router';

export const DASHBOARD_ROUTES: Routes = [
  { path: '', loadComponent: () => import('./dashboard.page').then(m => m.DashboardPage) },
  { path: 'mobile', data: { variant: 'mobile' }, loadComponent: () => import('./dashboard.page').then(m => m.DashboardPage) }
];
