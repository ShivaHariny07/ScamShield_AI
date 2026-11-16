import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, isAbortError } from "../../api/client";
import { getInvestigation, isTerminal, type Investigation } from "../../api/investigations";

const POLL_INTERVAL_MS = 2_000;
const MAX_CONSECUTIVE_ERRORS = 3;
const MAX_POLL_DURATION_MS = 5 * 60 * 1_000;

const TIMEOUT_MESSAGE =
  "Still processing after 5 minutes. Automatic refresh has paused — use “Refresh status” to check again.";

export interface InvestigationPolling {
  investigation: Investigation;
  error: string | null;
  /** True while automatic refresh is active. */
  polling: boolean;
  /** True while a manually requested refresh is in flight. */
  refreshing: boolean;
  /** Fetch immediately and resume automatic refresh if still in progress. */
  refresh: () => void;
}

export function useInvestigationPolling(initial: Investigation): InvestigationPolling {
  const [investigation, setInvestigation] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  // Incrementing runId restarts the polling loop (used by refresh()).
  const [runId, setRunId] = useState(0);

  const latestStatus = useRef(initial.status);
  latestStatus.current = investigation.status;

  const investigationId = initial.id;

  useEffect(() => {
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: number | undefined;
    let consecutiveErrors = 0;

    const schedule = () => {
      timer = window.setTimeout(() => void poll(false), POLL_INTERVAL_MS);
    };

    async function poll(manual: boolean) {
      if (!manual && Date.now() - startedAt > MAX_POLL_DURATION_MS) {
        setPaused(true);
        setError(TIMEOUT_MESSAGE);
        return;
      }
      if (manual) setRefreshing(true);
      try {
        const latest = await getInvestigation(investigationId, controller.signal);
        consecutiveErrors = 0;
        setInvestigation(latest);
        setError(null);
        if (!isTerminal(latest.status)) schedule();
      } catch (err) {
        if (isAbortError(err) || controller.signal.aborted) return;
        consecutiveErrors += 1;
        setError(err instanceof ApiError ? err.message : "Could not refresh the status.");
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          setPaused(true);
        } else {
          schedule();
        }
      } finally {
        if (manual && !controller.signal.aborted) setRefreshing(false);
      }
    }

    if (runId > 0) {
      void poll(true); // manual refresh: fetch now
    } else if (!isTerminal(latestStatus.current)) {
      schedule();
    }

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [investigationId, runId]);

  const refresh = useCallback(() => {
    setPaused(false);
    setError(null);
    setRunId((id) => id + 1);
  }, []);

  return {
    investigation,
    error,
    polling: !paused && !isTerminal(investigation.status),
    refreshing,
    refresh,
  };
}
