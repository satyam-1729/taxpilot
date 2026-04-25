import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header class="shell-header">
      <a routerLink="/" class="brand" aria-label="TaxPilot home">
        <span class="logo">TP</span>
      </a>

      @if (auth.isLoggedIn() && auth.isVerified()) {
        <nav class="nav">
          <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a>
          <a routerLink="/documents" routerLinkActive="active">Documents</a>
          <a routerLink="/savings" routerLinkActive="active">Savings</a>
          <a routerLink="/investments" routerLinkActive="active">Investments</a>
          <a routerLink="/chat" routerLinkActive="active">AI Chat</a>
          <a routerLink="/profile" routerLinkActive="active">Profile</a>
        </nav>
      } @else {
        <span class="spacer"></span>
      }

      <div class="auth-links">
        @if (auth.isLoggedIn()) {
          <button class="signout" (click)="signOut()">Sign out</button>
        } @else {
          <a routerLink="/signin" routerLinkActive="active" class="cta">Sign in</a>
        }
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
    .spacer { flex: 1; }
    .nav { display: flex; gap: 6px; flex: 1; }
    .nav a, .auth-links a {
      padding: 8px 14px; border-radius: 999px;
      color: #454652; text-decoration: none; font-size: 14px; font-weight: 500;
      transition: background 0.15s;
    }
    .nav a:hover, .auth-links a:hover { background: #f3f3f5; }
    .nav a.active, .auth-links a.active { background: #e0e0ff; color: #000666; }
    .auth-links { display: flex; gap: 6px; align-items: center; }
    .auth-links .cta { background: #000666; color: #fff; }
    .auth-links .cta:hover { background: #1a237e; }
    .signout {
      background: none; border: 0; cursor: pointer;
      padding: 8px 14px; border-radius: 999px;
      color: #454652; font-size: 14px; font-weight: 500; font-family: inherit;
      transition: background 0.15s;
    }
    .signout:hover { background: #f3f3f5; }
    .shell-main { flex: 1; overflow: hidden; }
  `]
})
export class ShellComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    if (this.auth.isLoggedIn()) {
      void this.auth.refresh();
    }
  }

  async signOut(): Promise<void> {
    await this.auth.signOut();
    await this.router.navigateByUrl('/signin');
  }
}
