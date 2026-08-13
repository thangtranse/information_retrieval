/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_ARTICLE_SOURCE_DOMAIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
