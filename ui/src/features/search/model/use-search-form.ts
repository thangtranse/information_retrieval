import { useCallback, useState } from "react";

interface SearchFormController {
  query: string;
  canSubmit: boolean;
  updateQuery: (query: string) => void;
  submit: () => string | null;
}

export function useSearchForm(): SearchFormController {
  const [query, setQuery] = useState("");
  const canSubmit = query.trim().length > 0;

  const submit = useCallback(() => {
    // WHY: The request boundary receives one normalized snapshot even if the editable value later changes.
    const normalizedQuery = query.trim();

    if (normalizedQuery.length === 0) return null;

    return normalizedQuery;
  }, [query]);

  return {
    query,
    canSubmit,
    updateQuery: setQuery,
    submit,
  };
}
