export type ArticleImportMode = "url" | "content";

export type ArticleImportDraft =
  { kind: "url"; url: string } | { kind: "content"; content: string };

export type ArticleUrlError =
  "required" | "invalid-url" | "unsupported-protocol" | "invalid-domain";

export interface ArticleUrlValidation {
  canonicalUrl: string | null;
  error: ArticleUrlError | null;
}

export function validateArticleUrl(rawUrl: string, sourceDomain: string): ArticleUrlValidation {
  // WHY: Validation and canonicalization share one parser so the accepted value always matches the payload.
  const candidate = rawUrl.trim();

  if (candidate.length === 0) return { canonicalUrl: null, error: "required" };

  let parsedUrl: URL;

  try {
    parsedUrl = new URL(candidate);
  } catch {
    return { canonicalUrl: null, error: "invalid-url" };
  }

  if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
    return { canonicalUrl: null, error: "unsupported-protocol" };
  }

  const allowedDomain = sourceDomain
    .trim()
    .toLowerCase()
    .replace(/^\.+|\.+$/g, "");
  const hostname = parsedUrl.hostname.toLowerCase().replace(/\.$/, "");
  const belongsToSource = hostname === allowedDomain || hostname.endsWith(`.${allowedDomain}`);

  if (!allowedDomain || !belongsToSource) {
    return { canonicalUrl: null, error: "invalid-domain" };
  }

  // WHY: Tracking parameters and fragments do not identify a different article and would create duplicates later.
  parsedUrl.search = "";
  parsedUrl.hash = "";

  return { canonicalUrl: parsedUrl.toString(), error: null };
}

export function normalizeArticleContent(content: string): string | null {
  // WHY: Whitespace-only records cannot provide searchable source material.
  const normalizedContent = content.trim();
  return normalizedContent.length > 0 ? normalizedContent : null;
}
