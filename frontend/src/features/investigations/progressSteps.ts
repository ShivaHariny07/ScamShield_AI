import type { Investigation } from "../../api/investigations";

/** Mirrors PROCESSING_STEPS in backend/app/services/processing.py. */
const PIPELINE_STEPS: { key: string; label: string }[] = [
  { key: "validating_submission", label: "Validating submission" },
  { key: "preparing_analysis", label: "Preparing for analysis" },
];

export type StepState = "done" | "current" | "upcoming" | "failed";

export interface DisplayStep {
  key: string;
  label: string;
  state: StepState;
}

/** Builds the progress rows shown to the user for an investigation. */
export function buildDisplaySteps(investigation: Investigation): DisplayStep[] {
  const { status, progress_step: progressStep } = investigation;

  const pipeline = [...PIPELINE_STEPS];
  // Unknown future steps are shown by their raw identifier, never hidden.
  if (
    (status === "processing" || status === "failed") &&
    progressStep &&
    !pipeline.some((step) => step.key === progressStep)
  ) {
    pipeline.push({ key: progressStep, label: progressStep });
  }

  const received: DisplayStep = {
    key: "received",
    label: status === "pending" ? "Received — waiting to start" : "Received",
    state: status === "pending" ? "current" : "done",
  };
  const finished: DisplayStep = {
    key: "finished",
    label: "Finished",
    state: status === "completed" ? "done" : "upcoming",
  };

  const activeIndex = pipeline.findIndex((step) => step.key === progressStep);
  const middle = pipeline.map((step, index): DisplayStep => {
    let state: StepState = "upcoming";
    if (status === "completed") {
      state = "done";
    } else if (status === "processing" || status === "failed") {
      if (index < activeIndex) state = "done";
      else if (index === activeIndex) state = status === "failed" ? "failed" : "current";
    }
    return { key: step.key, label: step.label, state };
  });

  return [received, ...middle, finished];
}
