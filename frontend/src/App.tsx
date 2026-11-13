import { useState } from "react";

import type { Investigation } from "./api/investigations";
import InvestigationResult from "./features/investigations/InvestigationResult";
import SubmissionForm from "./features/investigations/SubmissionForm";

export default function App() {
  const [investigation, setInvestigation] = useState<Investigation | null>(null);

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
      <div className="mx-auto max-w-2xl">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold">ScamShield AI</h1>
          <p className="mt-1 text-sm text-slate-600">
            Report a suspicious message to start a fraud investigation.
          </p>
        </header>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          {investigation ? (
            <InvestigationResult
              investigation={investigation}
              onUpdated={setInvestigation}
              onReset={() => setInvestigation(null)}
            />
          ) : (
            <SubmissionForm onCreated={setInvestigation} />
          )}
        </div>

        <p className="mt-4 text-center text-xs text-slate-500">
          Development build — not for public use.
        </p>
      </div>
    </main>
  );
}
