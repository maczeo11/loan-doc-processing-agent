/**
 * Firebase client init. This config (apiKey included) is meant to be public -
 * it identifies the project to Google's client SDK, it does not grant any
 * access on its own. Actual access control is the allowlist enforced
 * server-side (apps/api/auth/firebase_verify.py + AUTHORIZED_EMAILS /
 * AUTHORIZED_DOMAINS) and Firebase's own security rules, never this config.
 */
import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: 'AIzaSyBIqd0VUXNo-dRvVb29KrmeiBEg_4i4Iq4',
  authDomain: 'cognizant-77c1a.firebaseapp.com',
  projectId: 'cognizant-77c1a',
  storageBucket: 'cognizant-77c1a.firebasestorage.app',
  messagingSenderId: '38004194446',
  appId: '1:38004194446:web:2505803763127567899ddf',
  measurementId: 'G-4S9H8JLJYG',
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
