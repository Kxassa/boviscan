/**
 * Lazy Firebase Auth helpers.
 * Only imported when VITE_FIREBASE_AUTH_ENABLED=true and config is present.
 */

import {
  authEnabled,
  googleSignInConfigured,
  readFirebaseConfig,
  type FirebaseWebConfig,
} from "./config";
import { clearSession, setSession } from "./session";

type AuthMod = typeof import("firebase/auth");
type AppMod = typeof import("firebase/app");

let appInit: ReturnType<AppMod["initializeApp"]> | null = null;
let authInit: ReturnType<AuthMod["getAuth"]> | null = null;

async function getAuthInstance() {
  const cfg = readFirebaseConfig();
  if (!cfg) throw new Error("Firebase web config missing (VITE_FIREBASE_*)");
  const { initializeApp, getApps } = await import("firebase/app");
  const { getAuth, connectAuthEmulator } = await import("firebase/auth");
  if (!appInit) {
    appInit = getApps().length ? getApps()[0]! : initializeApp(cfg as FirebaseWebConfig);
    authInit = getAuth(appInit);
    const emu = import.meta.env.VITE_FIREBASE_AUTH_EMULATOR_HOST as string | undefined;
    if (emu) {
      connectAuthEmulator(authInit, emu.startsWith("http") ? emu : `http://${emu}`, {
        disableWarnings: true,
      });
    }
  }
  return authInit!;
}

export async function signInEmailPassword(email: string, password: string): Promise<void> {
  if (!authEnabled()) throw new Error("Auth disabled");
  const { signInWithEmailAndPassword } = await import("firebase/auth");
  const auth = await getAuthInstance();
  const cred = await signInWithEmailAndPassword(auth, email, password);
  const token = await cred.user.getIdToken();
  setSession(token, cred.user.email);
}

export async function signUpEmailPassword(email: string, password: string): Promise<void> {
  if (!authEnabled()) throw new Error("Auth disabled");
  const { createUserWithEmailAndPassword } = await import("firebase/auth");
  const auth = await getAuthInstance();
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  const token = await cred.user.getIdToken();
  setSession(token, cred.user.email);
}

export async function signInGoogle(): Promise<"ok" | "stub"> {
  if (!authEnabled()) throw new Error("Auth disabled");
  if (!googleSignInConfigured()) return "stub";
  const { GoogleAuthProvider, signInWithPopup } = await import("firebase/auth");
  const auth = await getAuthInstance();
  const provider = new GoogleAuthProvider();
  const cred = await signInWithPopup(auth, provider);
  const token = await cred.user.getIdToken();
  setSession(token, cred.user.email);
  return "ok";
}

export async function signOutFirebase(): Promise<void> {
  try {
    if (authEnabled() && readFirebaseConfig()) {
      const { signOut } = await import("firebase/auth");
      const auth = await getAuthInstance();
      await signOut(auth);
    }
  } finally {
    clearSession();
  }
}

export async function refreshIdToken(): Promise<string | null> {
  if (!authEnabled() || !readFirebaseConfig()) return null;
  try {
    const auth = await getAuthInstance();
    if (!auth.currentUser) return null;
    const token = await auth.currentUser.getIdToken(true);
    setSession(token, auth.currentUser.email);
    return token;
  } catch {
    return null;
  }
}
