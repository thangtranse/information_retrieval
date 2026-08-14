import { useMemo, useState } from "react";

import {
  buildManualArticleBlocks,
  normalizeArticleContent,
  validateArticleUrl,
  type ArticleImportDraft,
  type ArticleImportMode,
  type ArticleUrlError,
} from "@/features/article-import/model/article-import";

interface ArticleImportFormController {
  mode: ArticleImportMode;
  url: string;
  title: string;
  content: string;
  urlError: ArticleUrlError | null;
  titleError: boolean;
  contentError: boolean;
  canSubmit: boolean;
  changeMode: (mode: ArticleImportMode) => void;
  updateUrl: (url: string) => void;
  updateTitle: (title: string) => void;
  updateContent: (content: string) => void;
  blurUrl: () => void;
  blurContent: () => void;
  prepareSubmission: () => ArticleImportDraft | null;
}

export function useArticleImportForm(sourceDomain: string): ArticleImportFormController {
  const [mode, setMode] = useState<ArticleImportMode>("url");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [urlTouched, setUrlTouched] = useState(false);
  const [titleTouched, setTitleTouched] = useState(false);
  const [contentTouched, setContentTouched] = useState(false);
  const urlValidation = useMemo(() => validateArticleUrl(url, sourceDomain), [sourceDomain, url]);
  const normalizedContent = normalizeArticleContent(content);
  const manualBlocks = buildManualArticleBlocks(title, content);
  const canSubmit = mode === "url" ? urlValidation.canonicalUrl !== null : manualBlocks !== null;

  const changeMode = (nextMode: ArticleImportMode) => {
    // WHY: Each source keeps its draft across tabs, while stale success feedback must not cross modes.
    setMode(nextMode);
  };

  const updateUrl = (nextUrl: string) => {
    // WHY: Editing invalidates the previous prepared payload but preserves touched state for live correction.
    setUrl(nextUrl);
  };

  const updateTitle = (nextTitle: string) => {
    // WHY: Title identity remains independent from paragraph edits across tab switches.
    setTitle(nextTitle);
  };

  const updateContent = (nextContent: string) => {
    // WHY: Editing invalidates the previous prepared payload but keeps the alternate URL draft intact.
    setContent(nextContent);
  };

  const blurUrl = () => {
    // WHY: Canonicalizing on blur makes the exact future payload visible without interrupting typing.
    setUrlTouched(true);
    if (urlValidation.canonicalUrl) setUrl(urlValidation.canonicalUrl);
  };

  const blurContent = () => {
    // WHY: Delaying the required error until blur avoids flagging a field before the user interacts with it.
    setContentTouched(true);
  };

  const prepareSubmission = (): ArticleImportDraft | null => {
    // WHY: Validation produces the exact immutable payload consumed by the ordered API pipeline.
    if (mode === "url") {
      setUrlTouched(true);
      if (!urlValidation.canonicalUrl) return null;

      setUrl(urlValidation.canonicalUrl);
      return { kind: "url", url: urlValidation.canonicalUrl };
    }

    setTitleTouched(true);
    setContentTouched(true);
    if (!manualBlocks) return null;
    return { kind: "content", blocks: manualBlocks };
  };

  return {
    mode,
    url,
    title,
    content,
    urlError: urlTouched ? urlValidation.error : null,
    titleError: titleTouched && title.trim().length === 0,
    contentError: contentTouched && normalizedContent === null,
    canSubmit,
    changeMode,
    updateUrl,
    updateTitle,
    updateContent,
    blurUrl,
    blurContent,
    prepareSubmission,
  };
}
