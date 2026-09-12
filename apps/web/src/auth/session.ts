/** In-memory + localStorage session for Firebase ID token. */

const TOKEN_KEY = "boviscan_id_token";
const EMAIL_KEY = "boviscan_user_email";

let memoryToken: string | null = null;
let memoryEmail: string | null = null;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function subscribeAuth(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getIdToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = localStorage.getItem(TOKEN_KEY);
  } catch {
    memoryToken = null;
  }
  return memoryToken;
}

export function getUserEmail(): string | null {
  if (memoryEmail) return memoryEmail;
  try {
    memoryEmail = localStorage.getItem(EMAIL_KEY);
  } catch {
    memoryEmail = null;
  }
  return memoryEmail;
}

export function setSession(token: string, email: string | null) {
  memoryToken = token;
  memoryEmail = email;
  try {
    localStorage.setItem(TOKEN_KEY, token);
    if (email) localStorage.setItem(EMAIL_KEY, email);
    else localStorage.removeItem(EMAIL_KEY);
  } catch {
    /* ignore quota */
  }
  notify();
}

export function clearSession() {
  memoryToken = null;
  memoryEmail = null;
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  } catch {
    /* ignore */
  }
  notify();
}
