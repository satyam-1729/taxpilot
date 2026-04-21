# TaxPilot Frontend

Angular 18 (standalone components) + SCSS. Screens are sourced from the **Sovereign Ledger** design system in Stitch (project "India Tax AI Assistant") and served through a lightweight Angular shell with routing, lazy-loaded features, and a shared iframe host.

## Structure

```
src/
├── app/
│   ├── core/
│   │   ├── layout/          # App shell (header, nav, router-outlet)
│   │   └── services/        # Cross-cutting services (api, auth — TBD)
│   ├── shared/
│   │   └── stitch-frame/    # Reusable <app-stitch-frame file="..."> iframe host
│   ├── features/
│   │   ├── landing/
│   │   ├── auth/
│   │   │   ├── signin/
│   │   │   └── identity/
│   │   ├── dashboard/       # desktop + /mobile variant
│   │   ├── documents/       # Document Vault
│   │   ├── chat/            # AI Assistant Chat
│   │   ├── savings/         # Tax Savings Guide (desktop + /mobile)
│   │   ├── investments/     # Investment Insights (desktop + /mobile)
│   │   └── profile/
│   ├── app.component.ts
│   ├── app.config.ts
│   └── app.routes.ts        # Each feature lazy-loaded via its own routes file
├── styles.scss              # Global tokens (Sovereign Ledger palette)
└── index.html
public/
└── stitch/                  # Raw Stitch HTML exports (one per screen)
```

Each feature exposes its own `*.routes.ts` and standalone `*.page.ts`, so adding a new screen means dropping the HTML into `public/stitch/` and creating a feature folder.

## Screens wired up

| Route                  | File                    | Source                         |
|------------------------|-------------------------|--------------------------------|
| `/`                    | landing.html            | Sovereign Ledger Tax Assistant |
| `/signin`              | signin.html             | Sign In / Sign Up              |
| `/identity`            | identity.html           | Identity Verification          |
| `/dashboard`           | dashboard.html          | Tax Dashboard (desktop)        |
| `/dashboard/mobile`    | dashboard-mobile.html   | Tax Dashboard (mobile)         |
| `/documents`           | documents.html          | Document Vault                 |
| `/chat`                | chat.html               | AI Assistant Chat              |
| `/savings`             | savings.html            | Tax Savings Guide (desktop)    |
| `/savings/mobile`      | savings-mobile.html     | Tax Savings Guide (mobile)     |
| `/investments`         | investments.html        | Investment Insights (desktop)  |
| `/investments/mobile`  | investments-mobile.html | Investment Insights (mobile)   |
| `/profile`             | profile.html            | User Profile                   |

## Setup

```bash
npm install
npm start        # ng serve → http://localhost:4200
npm run build    # production bundle in dist/frontend
```

## Design tokens

Exposed as CSS custom properties in `styles.scss`:

- `--color-primary` `#000666` — trust anchor
- `--color-secondary` `#1b6d24` — financial health / success
- `--color-surface` `#f9f9fb` — base canvas
- Roundedness: `--radius-md` (0.75rem), `--radius-xl` (1.5rem)
- Fonts: **Manrope** (display/headline), **Inter** (body/label)

Follow the "No-Line Rule" and layered tonal surfaces rather than borders for sectioning — see the design system doc attached to the Stitch project.
