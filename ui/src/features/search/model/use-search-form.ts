import { useCallback, useState } from "react";

interface SearchFormController {
  query: string;
  submittedQuery: string | null;
  canSubmit: boolean;
  updateQuery: (query: string) => void;
  submit: () => void;
}

export function useSearchForm(): SearchFormController {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const canSubmit = query.trim().length > 0;

  const submit = useCallback(() => {
    // WHY: Keeping a normalized local snapshot creates the future API hand-off without faking a request now.
    const normalizedQuery = query.trim();

    if (normalizedQuery.length === 0) return;

    setSubmittedQuery(normalizedQuery);
  }, [query]);

  return {
    query,
    submittedQuery,
    canSubmit,
    updateQuery: setQuery,
    submit,
  };
}
