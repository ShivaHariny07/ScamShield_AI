import { useState, type FormEvent } from "react";

import { ApiError } from "../../api/client";
import {
  createInvestigation,
  MAX_TEXT_LENGTH,
  type IncidentType,
  type Investigation,
  type UserSourceType,
} from "../../api/investigations";
import ErrorAlert from "../../components/ErrorAlert";
import { INCIDENT_TYPE_OPTIONS } from "./incidentTypes";

interface SubmissionFormProps {
  onCreated: (investigation: Investigation) => void;
}

const SOURCE_OPTIONS: readonly [UserSourceType, string][] = [
  ["pasted_text", "I pasted it"],
  ["typed_text", "I typed it"],
];

export default function SubmissionForm({ onCreated }: SubmissionFormProps) {
  const [text, setText] = useState("");
  const [source, setSource] = useState<UserSourceType>("pasted_text");
  const [incidentType, setIncidentType] = useState<IncidentType | "">("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const tooLong = text.length > MAX_TEXT_LENGTH;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    if (text.trim().length === 0) {
      setError("Please paste or type the suspicious message.");
      return;
    }
    if (tooLong) {
      setError(
        `The message is too long (maximum ${MAX_TEXT_LENGTH.toLocaleString()} characters).`,
      );
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      const investigation = await createInvestigation({
        submission_type: "text",
        incident_type: incidentType === "" ? null : incidentType,
        // Sent verbatim: the submitted text is evidence.
        initial_message: { original_text: text, submission_source_type: source },
      });
      onCreated(investigation);
    } catch (err) {
      // The entered text is kept so the user can retry.
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const fieldClass =
    "mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-sky-500 focus:ring-2 focus:ring-sky-200 focus:outline-none";

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div>
        <label htmlFor="message" className="block text-sm font-medium text-slate-800">
          Suspicious message
        </label>
        <textarea
          id="message"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={8}
          placeholder="Paste the SMS, WhatsApp or email text you received…"
          className={fieldClass}
        />
        <p className={`mt-1 text-right text-xs ${tooLong ? "text-red-700" : "text-slate-500"}`}>
          {text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}
        </p>
      </div>

      <fieldset>
        <legend className="text-sm font-medium text-slate-800">How did you get this text?</legend>
        <div className="mt-2 flex flex-wrap gap-4 text-sm text-slate-700">
          {SOURCE_OPTIONS.map(([value, label]) => (
            <label key={value} className="flex items-center gap-2">
              <input
                type="radio"
                name="source"
                value={value}
                checked={source === value}
                onChange={() => setSource(value)}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="incident" className="block text-sm font-medium text-slate-800">
          What happened? <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <select
          id="incident"
          value={incidentType}
          onChange={(event) => setIncidentType(event.target.value as IncidentType | "")}
          className={fieldClass}
        >
          <option value="">Not sure / skip</option>
          {INCIDENT_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {error && <ErrorAlert message={error} />}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-sky-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? "Submitting…" : "Start investigation"}
      </button>
    </form>
  );
}
