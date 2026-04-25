import { initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';
import { environment } from '../../../environments/environment';

let _app: FirebaseApp | null = null;
let _auth: Auth | null = null;

export function firebaseApp(): FirebaseApp {
  if (!_app) {
    _app = initializeApp(environment.firebase);
  }
  return _app;
}

export function firebaseAuth(): Auth {
  if (!_auth) {
    _auth = getAuth(firebaseApp());
  }
  return _auth;
}
