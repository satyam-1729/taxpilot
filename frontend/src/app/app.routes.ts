import { Routes } from '@angular/router';

import { ShellComponent } from './core/layout/shell.component';
import { verifiedGuard } from './core/auth/guards';

export const routes: Routes = [
  {
    path: '',
    component: ShellComponent,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: '', loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES) },
      {
        path: 'dashboard',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES),
      },
      {
        path: 'documents',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/documents/documents.routes').then(m => m.DOCUMENTS_ROUTES),
      },
      {
        path: 'chat',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/chat/chat.routes').then(m => m.CHAT_ROUTES),
      },
      {
        path: 'savings',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/savings/savings.routes').then(m => m.SAVINGS_ROUTES),
      },
      {
        path: 'investments',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/investments/investments.routes').then(m => m.INVESTMENTS_ROUTES),
      },
      {
        path: 'profile',
        canActivate: [verifiedGuard],
        loadChildren: () => import('./features/profile/profile.routes').then(m => m.PROFILE_ROUTES),
      },
      { path: '**', redirectTo: 'dashboard' },
    ],
  },
];
