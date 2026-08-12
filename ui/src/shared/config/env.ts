const DEFAULT_API_BASE_URL = "http://localhost:8000";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

export const env = Object.freeze({
  // WHY: Normalizing once prevents feature gateways from producing URLs with accidental `//`.
  apiBaseUrl: configuredApiBaseUrl.replace(/\/+$/, ""),
});
