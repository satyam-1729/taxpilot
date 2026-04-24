import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="shell-header">
      <a routerLink="/" class="brand" aria-label="TaxPilot home">
        <span class="logo">TP</span>
      </a>
      <nav class="nav">
        <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a>
        <a routerLink="/documents" routerLinkActive="active">Documents</a>
        <a routerLink="/savings" routerLinkActive="active">Savings</a>
        <a routerLink="/investments" routerLinkActive="active">Investments</a>
        <a routerLink="/chat" routerLinkActive="active">AI Chat</a>
        <a routerLink="/profile" routerLinkActive="active">Profile</a>
      </nav>
      <div class="auth-links">
        <a routerLink="/signin" routerLinkActive="active">Sign In</a>
        <a routerLink="/identity" routerLinkActive="active" class="cta">Verify</a>
      </div>
    </header>
    <main class="shell-main">
      <router-outlet />
    </main>
  `,
  styles: [`
    :host { display: flex; flex-direction: column; height: 100vh; font-family: 'Inter', system-ui, sans-serif; }
    .shell-header {
      display: flex; align-items: center; gap: 32px;
      height: 64px; padding: 0 24px;
      background: #ffffff; color: #1a1c1d;
      border-bottom: 1px solid rgba(198,197,212,0.4);
      position: sticky; top: 0; z-index: 10;
    }
    .brand { display: flex; align-items: center; text-decoration: none; }
    .logo {
      display: inline-flex; align-items: center; justify-content: center;
      width: 36px; height: 36px; border-radius: 10px;
      background: #000666; color: #ffffff;
      font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 16px;
      letter-spacing: -0.04em;
    }
    .nav { display: flex; gap: 6px; flex: 1; }
    .nav a, .auth-links a {
      padding: 8px 14px; border-radius: 999px;
      color: #454652; text-decoration: none; font-size: 14px; font-weight: 500;
      transition: background 0.15s;
    }
    .nav a:hover, .auth-links a:hover { background: #f3f3f5; }
    .nav a.active, .auth-links a.active { background: #e0e0ff; color: #000666; }
    .auth-links { display: flex; gap: 6px; }
    .auth-links .cta { background: #000666; color: #fff; }
    .auth-links .cta:hover { background: #1a237e; }
    .shell-main { flex: 1; overflow: hidden; }
  `]
})
export class ShellComponent {}
