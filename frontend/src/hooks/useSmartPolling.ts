import { useEffect, useRef, useCallback, useState } from "react";

interface UseSmartPollingOptions {
  /** Polling interval in milliseconds */
  intervalMs: number;
  /** Callback to execute on each poll */
  onPoll: () => Promise<void> | void;
  /** Whether polling is enabled */
  enabled?: boolean;
  /** Maximum backoff multiplier on errors */
  maxBackoffMultiplier?: number;
}

/**
 * Smart polling hook with visibility awareness and exponential backoff.
 *
 * Features:
 * - Pauses polling when browser tab is not visible (Page Visibility API)
 * - Uses exponential backoff on errors (up to maxBackoffMultiplier)
 * - Cleans up on unmount
 * - Immediately polls when tab becomes visible after being hidden
 */
export function useSmartPolling({
  intervalMs,
  onPoll,
  enabled = true,
  maxBackoffMultiplier = 4,
}: UseSmartPollingOptions) {
  const intervalRef = useRef<number | null>(null);
  const [backoff, setBackoff] = useState(1);
  const isVisibleRef = useRef(!document.hidden);
  const lastPollTimeRef = useRef<number>(0);

  const poll = useCallback(async () => {
    if (!isVisibleRef.current || !enabled) return;

    try {
      await onPoll();
      setBackoff(1); // Reset backoff on success
      lastPollTimeRef.current = Date.now();
    } catch {
      // Increase backoff on error (max 4x)
      setBackoff((prev: number) => Math.min(prev * 2, maxBackoffMultiplier));
    }
  }, [onPoll, enabled, maxBackoffMultiplier]);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    const effectiveInterval = intervalMs * backoff;

    intervalRef.current = window.setInterval(() => {
      poll();
    }, effectiveInterval);
  }, [intervalMs, poll, backoff]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Handle visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      if (document.hidden) {
        // Tab is hidden - stop polling to save resources
        stopPolling();
      } else {
        // Tab is visible again
        const timeSinceLastPoll = Date.now() - lastPollTimeRef.current;

        // If it's been longer than the interval, poll immediately
        if (timeSinceLastPoll > intervalMs) {
          poll();
        }

        // Resume polling
        if (enabled) {
          startPolling();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [intervalMs, poll, startPolling, stopPolling, enabled]);

  // Start/stop polling based on enabled state
  useEffect(() => {
    if (enabled && isVisibleRef.current) {
      // Initial poll - wrap in setTimeout to avoid synchronous setState warning in effect
      const timer = setTimeout(() => {
        poll();
        startPolling();
      }, 0);
      return () => {
        clearTimeout(timer);
        stopPolling();
      };
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, poll, startPolling, stopPolling]);

  return {
    /** Force an immediate poll */
    pollNow: poll,
    /** Current backoff multiplier (for debugging) */
    backoffMultiplier: backoff,
  };
}
