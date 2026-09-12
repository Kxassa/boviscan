import { FormEvent, useState } from "react";
import { authEnabled, googleSignInConfigured, readFirebaseConfig } from "../auth/config";
import {
  signInEmailPassword,
  signInGoogle,
  signUpEmailPassword,
} from "../auth/firebase";
import type { Locale } from "../i18n";
import { t } from "../i18n";

type Props = {
  locale: Locale;
  onAuthenticated: () => void;
};

export function LoginScreen({ locale, onAuthenticated }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"in" | "up">("in");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const cfg = readFirebaseConfig();
  const ready = authEnabled() && !!cfg;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    if (!ready) {
      setError(t("auth.configMissing", locale));
      return;
    }
    setBusy(true);
    try {
      if (mode === "in") await signInEmailPassword(email, password);
      else await signUpEmailPassword(email, password);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const onGoogle = async () => {
    setError(null);
    setInfo(null);
    if (!ready) {
      setError(t("auth.configMissing", locale));
      return;
    }
    setBusy(true);
    try {
      const r = await signInGoogle();
      if (r === "stub") {
        setInfo(t("auth.googleStub", locale));
      } else {
        onAuthenticated();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card login-card">
      <h2>{t("auth.heading", locale)}</h2>
      <p className="muted">{t("auth.intro", locale)}</p>
      {!ready && (
        <p className="pill warn">{t("auth.configMissing", locale)}</p>
      )}
      <form onSubmit={submit} className="login-form">
        <label>
          {t("auth.email", locale)}
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          {t("auth.password", locale)}
          <input
            type="password"
            autoComplete={mode === "in" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>
        <div className="login-actions">
          <button type="submit" disabled={busy || !ready}>
            {mode === "in" ? t("auth.signIn", locale) : t("auth.signUp", locale)}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => setMode(mode === "in" ? "up" : "in")}
          >
            {mode === "in" ? t("auth.needAccount", locale) : t("auth.haveAccount", locale)}
          </button>
        </div>
      </form>
      <hr />
      <button type="button" disabled={busy || !ready} onClick={onGoogle}>
        {googleSignInConfigured()
          ? t("auth.google", locale)
          : t("auth.googleStubButton", locale)}
      </button>
      {error && <p className="auth-error">{error}</p>}
      {info && <p className="muted">{info}</p>}
      <p className="muted">{t("auth.project", locale)}: boviscan-c2430</p>
    </div>
  );
}
