import { Routes } from '@angular/router';
import { ShellComponent } from './core/layout/shell.component';

export const routes: Routes = [
  {
    path: '',
    component: ShellComponent,
    children: [
      { path: '', loadChildren: () => import('./features/landing/landing.routes').then(m => m.LANDING_ROUTES) },
      { path: '', loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES) },
      { path: 'dashboard', loadChildren: () => import('./features/dashboard/dashboard.routes').then(m => m.DASHBOARD_ROUTES) },
      { path: 'documents', loadChildren: () => import('./features/documents/documents.routes').then(m => m.DOCUMENTS_ROUTES) },
      { path: 'chat', loadChildren: () => import('./features/chat/chat.routes').then(m => m.CHAT_ROUTES) },
      { path: 'savings', loadChildren: () => import('./features/savings/savings.routes').then(m => m.SAVINGS_ROUTES) },
      { path: 'investments', loadChildren: () => import('./features/investments/investments.routes').then(m => m.INVESTMENTS_ROUTES) },
      { path: 'profile', loadChildren: () => import('./features/profile/profile.routes').then(m => m.PROFILE_ROUTES) },
      { path: '**', redirectTo: '' }
    ]
  }
];
