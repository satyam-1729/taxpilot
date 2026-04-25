import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isLoggedIn()) {
    return router.createUrlTree(['/signin']);
  }
  return true;
};

export const verifiedGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isLoggedIn()) {
    return router.createUrlTree(['/signin']);
  }
  if (!auth.isVerified()) {
    return router.createUrlTree(['/identity']);
  }
  return true;
};

/** Bounce already-signed-in users away from /signin. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isLoggedIn()) {
    return router.createUrlTree([auth.isVerified() ? '/dashboard' : '/identity']);
  }
  return true;
};
