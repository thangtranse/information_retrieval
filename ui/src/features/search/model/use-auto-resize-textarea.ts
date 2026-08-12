import { useLayoutEffect, useRef } from "react";

const MIN_ROWS = 3;
const MAX_ROWS = 10;
const FALLBACK_LINE_HEIGHT_PX = 24;

export function useAutoResizeTextarea(value: string) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    // WHY: Clamping measured content height preserves long-query context without letting the form consume the page.
    const textarea = textareaRef.current;

    if (!textarea) return;

    const styles = window.getComputedStyle(textarea);
    const parsedLineHeight = Number.parseFloat(styles.lineHeight);
    const lineHeight = Number.isFinite(parsedLineHeight)
      ? parsedLineHeight
      : FALLBACK_LINE_HEIGHT_PX;
    const verticalPadding =
      Number.parseFloat(styles.paddingTop) + Number.parseFloat(styles.paddingBottom);
    const verticalBorder =
      Number.parseFloat(styles.borderTopWidth) + Number.parseFloat(styles.borderBottomWidth);
    const minHeight = lineHeight * MIN_ROWS + verticalPadding + verticalBorder;
    const maxHeight = lineHeight * MAX_ROWS + verticalPadding + verticalBorder;

    textarea.style.height = "auto";

    const contentHeight = textarea.scrollHeight + verticalBorder;
    textarea.style.height = `${Math.min(Math.max(contentHeight, minHeight), maxHeight)}px`;
    textarea.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
  }, [value]);

  return textareaRef;
}
