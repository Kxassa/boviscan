/** Firebase web config from Vite env — no secrets committed. */

export type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId?: string;
};

export function authEnabled(): boolean {
  const v = import.meta.env.VITE_FIREBASE_AUTH_ENABLED;
  return v === "true" || v === "1";
}

export function readFirebaseConfig(): FirebaseWebConfig | null {
  const apiKey = import.meta.env.VITE_FIREBASE_API_KEY as string | undefined;
  const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined;
  const projectId =
    (import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined) || "boviscan-c2430";
  const appId = import.meta.env.VITE_FIREBASE_APP_ID as string | undefined;
  if (!apiKey || !authDomain) return null;
  return { apiKey, authDomain, projectId, appId };
}

export function googleSignInConfigured(): boolean {
  // Explicit opt-in; without a real OAuth client Google is stubbed in the UI
  return import.meta.env.VITE_FIREBASE_GOOGLE_ENABLED === "true";
}
