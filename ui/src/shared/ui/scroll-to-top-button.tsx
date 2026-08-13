import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

import { Button } from "@/shared/ui/button";

const SCROLL_VISIBILITY_THRESHOLD = 400;

export function ScrollToTopButton() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const updateVisibility = () => {
      // WHY: A meaningful threshold avoids distracting users while they are still near page context.
      setIsVisible(window.scrollY > SCROLL_VISIBILITY_THRESHOLD);
    };

    updateVisibility();
    window.addEventListener("scroll", updateVisibility, { passive: true });
    return () => window.removeEventListener("scroll", updateVisibility);
  }, []);

  if (!isVisible) return null;

  const scrollToTop = () => {
    // WHY: Respecting reduced motion keeps this navigation aid usable for motion-sensitive users.
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: reducedMotion ? "auto" : "smooth" });
  };

  return (
    <Button
      aria-label="Lên đầu trang"
      className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1rem,env(safe-area-inset-bottom))] z-50 size-11 rounded-full shadow-lg shadow-black/20"
      onClick={scrollToTop}
      size="icon-lg"
      title="Lên đầu trang"
      type="button"
    >
      <ArrowUp aria-hidden="true" />
    </Button>
  );
}
