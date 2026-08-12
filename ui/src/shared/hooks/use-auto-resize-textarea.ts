import { useLayoutEffect, useRef } from "react";

const FALLBACK_LINE_HEIGHT_PX = 24;

interface AutoResizeTextareaOptions {
  minRows: number;
  maxRows: number;
  enabled?: boolean;
}

export function useAutoResizeTextarea(
  value: string,
  { minRows, maxRows, enabled = true }: AutoResizeTextareaOptions,
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    // WHY: Clamping measured content height preserves source context without letting a form consume the page.
    const textarea = textareaRef.current;

    if (!textarea || !enabled) return;

    const styles = window.getComputedStyle(textarea);
    const parsedLineHeight = Number.parseFloat(styles.lineHeight);
    const lineHeight = Number.isFinite(parsedLineHeight)
      ? parsedLineHeight
      : FALLBACK_LINE_HEIGHT_PX;
    const verticalPadding =
      Number.parseFloat(styles.paddingTop) + Number.parseFloat(styles.paddingBottom);
    const verticalBorder =
      Number.parseFloat(styles.borderTopWidth) + Number.parseFloat(styles.borderBottomWidth);
    const minHeight = lineHeight * minRows + verticalPadding + verticalBorder;
    const maxHeight = lineHeight * maxRows + verticalPadding + verticalBorder;

    textarea.style.height = "auto";

    const contentHeight = textarea.scrollHeight + verticalBorder;
    textarea.style.height = `${Math.min(Math.max(contentHeight, minHeight), maxHeight)}px`;
    textarea.style.overflowY = contentHeight > maxHeight ? "auto" : "hidden";
  }, [enabled, maxRows, minRows, value]);

  return textareaRef;
}
