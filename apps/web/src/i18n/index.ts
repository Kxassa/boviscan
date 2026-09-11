import ptBR from "./locales/pt-BR.json";
import en from "./locales/en.json";
import es from "./locales/es.json";

/** Sole ship locale for farmer-facing UI in v1. */
export const DEFAULT_LOCALE = "pt-BR" as const;

export type Locale = "pt-BR" | "en" | "es";

const catalogs: Record<Locale, Record<string, string>> = {
  "pt-BR": ptBR as Record<string, string>,
  en: en as Record<string, string>,
  es: es as Record<string, string>,
};

/** Optional stubs for engineering; product default remains pt-BR. */
export const OPTIONAL_LOCALES: Locale[] = ["en", "es"];

export function t(key: string, locale: Locale = DEFAULT_LOCALE): string {
  const primary = catalogs[locale]?.[key];
  if (primary && !key.startsWith("_")) return primary;
  return catalogs[DEFAULT_LOCALE][key] ?? key;
}

export function isShipLocale(locale: string): boolean {
  return locale === DEFAULT_LOCALE;
}
