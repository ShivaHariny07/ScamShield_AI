import type { Investigation } from "../../api/investigations";
import { buildDisplaySteps, type StepState } from "./progressSteps";

interface ProgressTrackerProps {
  investigation: Investigation;
}

const STATE_STYLES: Record<StepState, { marker: string; text: string; srLabel: string }> = {
  done: { marker: "border-emerald-600 bg-emerald-600 text-white", text: "text-slate-800", srLabel: "done" },
  current: { marker: "border-sky-600 bg-white text-sky-700", text: "font-semibold text-sky-900", srLabel: "in progress" },
  failed: { marker: "border-red-600 bg-red-600 text-white", text: "font-semibold text-red-800", srLabel: "failed" },
  upcoming: { marker: "border-slate-300 bg-white text-slate-400", text: "text-slate-500", srLabel: "not started" },
};

function Marker({ state }: { state: StepState }) {
  if (state === "done") return <span aria-hidden="true">✓</span>;
  if (state === "failed") return <span aria-hidden="true">✕</span>;
  if (state === "current") {
    return (
      <span
        aria-hidden="true"
        className="block h-3 w-3 animate-spin rounded-full border-2 border-sky-600 border-t-transparent"
      />
    );
  }
  return <span aria-hidden="true" className="block h-1.5 w-1.5 rounded-full bg-slate-300" />;
}

export default function ProgressTracker({ investigation }: ProgressTrackerProps) {
  const steps = buildDisplaySteps(investigation);
  const current = steps.find((step) => step.state === "current" || step.state === "failed");

  return (
    <div>
      <h2 className="text-sm font-medium text-slate-800">Progress</h2>
      <ol className="mt-2 space-y-2">
        {steps.map((step) => {
          const style = STATE_STYLES[step.state];
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-xs ${style.marker}`}
              >
                <Marker state={step.state} />
              </span>
              <span className={style.text}>
                {step.label}
                <span className="sr-only"> ({style.srLabel})</span>
              </span>
            </li>
          );
        })}
      </ol>
      <p className="sr-only" aria-live="polite">
        {current ? `${current.label}: ${STATE_STYLES[current.state].srLabel}` : ""}
      </p>
    </div>
  );
}
