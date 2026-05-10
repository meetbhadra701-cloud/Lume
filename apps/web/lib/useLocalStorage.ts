"use client";

import { startTransition, useCallback, useEffect, useState } from "react";

/**
 * SSR-safe localStorage hook.
 * Initial state is `initial`; hydrates from localStorage after mount.
 * `set` persists and updates state; `clear` removes the key and resets to `initial`.
 */
export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(initial);

  // Hydrate from localStorage after mount (client-side only)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw != null) {
        const parsed = JSON.parse(raw) as T;
        startTransition(() => setValue(parsed));
      }
    } catch {
      // storage unavailable or parse error — stay with initial
    }
  }, [key]);

  const set = useCallback(
    (v: T) => {
      setValue(v);
      try {
        localStorage.setItem(key, JSON.stringify(v));
      } catch {
        // ignore quota / private-mode errors
      }
    },
    [key]
  );

  const clear = useCallback(() => {
    setValue(initial);
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  // `initial` is intentionally excluded — it's the mount-time value and won't change meaningfully

  return [value, set, clear] as const;
}
