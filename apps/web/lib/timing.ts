/**
 * WPM timing utilities — sliding window rolling average (DSA: O(1) amortized push).
 *
 * RollingAverage maintains a fixed-size circular buffer of recent samples and
 * exposes a running mean in O(1) time.  This is the "sliding window" DSA row
 * in docs/DSA_INVENTORY.md.
 */

export class RollingAverage {
  private readonly window: number[];
  private readonly size: number;
  private head: number = 0;
  private count: number = 0;
  private sum: number = 0;

  constructor(windowSize: number = 5) {
    if (windowSize < 1) throw new Error("windowSize must be ≥ 1");
    this.size = windowSize;
    this.window = new Array<number>(windowSize).fill(0);
  }

  /** Push a new sample; evicts the oldest when full. O(1). */
  push(value: number): void {
    if (this.count === this.size) {
      // Evict oldest
      this.sum -= this.window[this.head];
    } else {
      this.count += 1;
    }
    this.window[this.head] = value;
    this.sum += value;
    this.head = (this.head + 1) % this.size;
  }

  /** Current rolling average, or null if no samples yet. */
  get average(): number | null {
    return this.count === 0 ? null : this.sum / this.count;
  }

  /** Number of samples currently in the window. */
  get length(): number {
    return this.count;
  }

  reset(): void {
    this.window.fill(0);
    this.head = 0;
    this.count = 0;
    this.sum = 0;
  }
}

/**
 * WPMClock — tracks elapsed reading time to compute WPM.
 *
 * Rules per plan §A.23 / §4.3:
 *  - State starts null; first startIfIdle() call sets the clock.
 *  - Multiple start() calls are idempotent — only the first wins.
 *  - Reset on new passage or new config.
 *  - stop() returns elapsed ms (or null if never started).
 */
export class WPMClock {
  private startMs: number | null = null;
  private stopMs: number | null = null;

  /** Start the clock if not already running. */
  startIfIdle(): void {
    if (this.startMs === null) {
      this.startMs = Date.now();
    }
  }

  /** Stop the clock. Returns elapsed ms, or null if never started. */
  stop(): number | null {
    if (this.startMs === null) return null;
    this.stopMs = Date.now();
    return this.stopMs - this.startMs;
  }

  /** Compute WPM from word count. Returns null if clock was never started. */
  wpm(wordCount: number): number | null {
    const elapsed = this.stopMs
      ? this.stopMs - this.startMs!
      : this.startMs !== null
      ? Date.now() - this.startMs
      : null;
    if (elapsed === null || elapsed <= 0) return null;
    const minutes = elapsed / 60_000;
    return Math.round(wordCount / minutes);
  }

  reset(): void {
    this.startMs = null;
    this.stopMs = null;
  }
}
