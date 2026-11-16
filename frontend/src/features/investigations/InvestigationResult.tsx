import { useEffect, useState } from "react";

import type { Investigation } from "../../api/investigations";
import ErrorAlert from "../../components/ErrorAlert";
import ProgressTracker from "./ProgressTracker";
import { useInvestigationPolling } from "./useInvestigationPolling";

interface InvestigationResultProps {
  investigation: Investigation;
  onUpdated: (investigation: Investigation) => void;
  onReset: () => void;
}

const STATUS_STYLES: Record<Investigation["status"], string> = {
  pending: "bg-amber-100 text-amber-900",
  processing: "bg-sky-100 text-sky-900",
  completed: "bg-emerald-100 text-emerald-900",
  failed: "bg-red-100 text-red-900",
};

const NOT_ASSESSED_NOTE =
  "Automated analysis is not available yet. This investigation has been recorded but not assessed — do not assume the message is safe.";
const COMPLETED_NOTE =
  "Processing finished. Automated scam analysis is not available yet — this message has not been assessed. Do not assume it is safe.";
const DEFAULT_FAILURE = "Processing failed. Please try again later.";

export default function InvestigationResult({
  investigation: initial,
  onUpdated,
  onReset,
}: InvestigationResultProps) {
  const { investigation, error, polling, refreshing, refresh } = useInvestigationPolling(initial);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Keep the parent in sync with the latest polled state.
  useEffect(() => {
    if (investigation !== initial) onUpdated(investigation);
  }, [investigation, initial, onUpdated]);

  async function copyId() {
    try {
      await navigator.clipboard.writeText(investigation.id);
      setCopyError(null);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError("Could not copy automatically. Please select and copy the ID.");
    }
  }

  return (
    <section className="space-y-5">
      <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        Your investigation has been recorded.
      </div>

      <dl className="space-y-4 text-sm">
        <div>
          <dt className="font-medium text-slate-800">Investigation ID</dt>
          <dd className="mt-1 flex flex-wrap items-center gap-2">
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-xs break-all text-slate-900">
              {investigation.id}
            </code>
            <button
              type="button"
              onClick={copyId}
              className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-100"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-800">Status</dt>
          <dd className="mt-1 flex flex-wrap items-center gap-3">
            <span
              className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${STATUS_STYLES[investigation.status]}`}
            >
              {investigation.status}
            </span>
            {polling && <span className="text-xs text-slate-500">Updating automatically…</span>}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-slate-800">Created</dt>
          <dd className="mt-1 text-slate-700">
            {new Date(investigation.created_at).toLocaleString()}
          </dd>
        </div>
      </dl>

      <ProgressTracker investigation={investigation} />

      {investigation.status === "failed" && (
        <ErrorAlert message={investigation.error_message ?? DEFAULT_FAILURE} />
      )}

      <p className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        {investigation.status === "completed" ? COMPLETED_NOTE : NOT_ASSESSED_NOTE}
      </p>

      {error && <ErrorAlert message={error} />}
      {copyError && <ErrorAlert message={copyError} />}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100 disabled:opacity-60"
        >
          {refreshing ? "Refreshing…" : "Refresh status"}
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800"
        >
          Start a new investigation
        </button>
      </div>
    </section>
  );
}
