import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { AdaptationConfig } from "./types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Deep-equality check for AdaptationConfig (7 known keys). */
export function configsEqual(a: AdaptationConfig, b: AdaptationConfig): boolean {
  const keys = Object.keys(a) as (keyof AdaptationConfig)[];
  return keys.every((k) => a[k] === b[k]);
}
