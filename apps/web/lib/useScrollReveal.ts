"use client";

import { startTransition, useEffect, useRef, useState } from "react";

/**
 * Fires `shown = true` the first time the element scrolls into view.
 * Pair with `.lume-reveal[data-shown="true"]` CSS class for staggered reveals.
 */
export function useScrollReveal<T extends HTMLElement>(
  threshold = 0.15,
  rootMargin = "0px 0px -6% 0px"
) {
  const ref = useRef<T | null>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Skip observer in test / SSR environments
    if (typeof IntersectionObserver === "undefined") {
      startTransition(() => setShown(true));
      return;
    }

    // If already in the viewport when the effect runs (e.g. after a phase
    // transition that returns the element to an already-scrolled position),
    // reveal immediately without waiting for the IO callback.
    const { top, bottom } = el.getBoundingClientRect();
    if (top < window.innerHeight && bottom > 0) {
      setShown(true);
      return;
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          startTransition(() => setShown(true));
          io.disconnect();
        }
      },
      { threshold, rootMargin }
    );

    io.observe(el);
    return () => io.disconnect();
  }, [threshold, rootMargin]);

  return { ref, shown };
}
