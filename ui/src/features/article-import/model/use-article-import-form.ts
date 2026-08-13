import { useMemo, useState } from "react";

import {
  normalizeArticleContent,
  validateArticleUrl,
  type ArticleImportDraft,
  type ArticleImportMode,
  type ArticleUrlError,
} from "@/features/article-import/model/article-import";

interface ArticleImportFormController {
  mode: ArticleImportMode;
  url: string;
  content: string;
  urlError: ArticleUrlError | null;
  contentError: boolean;
  canSubmit: boolean;
  submittedDraft: ArticleImportDraft | null;
  changeMode: (mode: ArticleImportMode) => void;
  updateUrl: (url: string) => void;
  updateContent: (content: string) => void;
  blurUrl: () => void;
  blurContent: () => void;
  submit: () => void;
}

export function useArticleImportForm(sourceDomain: string): ArticleImportFormController {
  const [mode, setMode] = useState<ArticleImportMode>("url");
  const [url, setUrl] = useState("");
  const [content, setContent] = useState("");
  const [urlTouched, setUrlTouched] = useState(false);
  const [contentTouched, setContentTouched] = useState(false);
  const [submittedDraft, setSubmittedDraft] = useState<ArticleImportDraft | null>(null);
  const urlValidation = useMemo(() => validateArticleUrl(url, sourceDomain), [sourceDomain, url]);
  const normalizedContent = normalizeArticleContent(content);
  const canSubmit =
    mode === "url" ? urlValidation.canonicalUrl !== null : normalizedContent !== null;

  const changeMode = (nextMode: ArticleImportMode) => {
    // WHY: Each source keeps its draft across tabs, while stale success feedback must not cross modes.
    setMode(nextMode);
    setSubmittedDraft(null);
  };

  const updateUrl = (nextUrl: string) => {
    // WHY: Editing invalidates the previous prepared payload but preserves touched state for live correction.
    setUrl(nextUrl);
    setSubmittedDraft(null);
  };

  const updateContent = (nextContent: string) => {
    // WHY: Editing invalidates the previous prepared payload but keeps the alternate URL draft intact.
    setContent(nextContent);
    setSubmittedDraft(null);
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

  const submit = () => {
    // WHY: Local drafts define the future API boundary without implying that persistence already occurred.
    if (mode === "url") {
      setUrlTouched(true);
      if (!urlValidation.canonicalUrl) return;

      setUrl(urlValidation.canonicalUrl);
      setSubmittedDraft({ kind: "url", url: urlValidation.canonicalUrl });
      return;
    }

    setContentTouched(true);
    if (!normalizedContent) return;

    setSubmittedDraft({ kind: "content", content: normalizedContent });
  };

  return {
    mode,
    url,
    content,
    urlError: urlTouched ? urlValidation.error : null,
    contentError: contentTouched && normalizedContent === null,
    canSubmit,
    submittedDraft,
    changeMode,
    updateUrl,
    updateContent,
    blurUrl,
    blurContent,
    submit,
  };
}
