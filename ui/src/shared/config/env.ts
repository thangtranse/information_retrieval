const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_ARTICLE_SOURCE_DOMAIN = "vnexpress.net";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
const configuredArticleSourceDomain =
  import.meta.env.VITE_ARTICLE_SOURCE_DOMAIN ?? DEFAULT_ARTICLE_SOURCE_DOMAIN;

export const env = Object.freeze({
  // WHY: Normalizing once prevents feature gateways from producing URLs with accidental `//`.
  apiBaseUrl: configuredApiBaseUrl.replace(/\/+$/, ""),
  // WHY: A canonical host value keeps domain validation exact across local and container builds.
  articleSourceDomain:
    configuredArticleSourceDomain
      .trim()
      .toLowerCase()
      .replace(/^\.+|\.+$/g, "") || DEFAULT_ARTICLE_SOURCE_DOMAIN,
});
