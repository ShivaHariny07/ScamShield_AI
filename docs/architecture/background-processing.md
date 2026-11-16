# Background processing (Milestone 3)

Investigations are processed after the HTTP response is sent, using
**FastAPI BackgroundTasks** (in-process; no Redis, Celery or other queue).
Implementation: `backend/app/services/processing.py`.

## When processing runs

`POST /api/v1/investigations` schedules processing **only when the request
includes `initial_message`**. Investigations created without one stay
`pending`; adding messages later does not start processing.

The response is returned immediately with `status: "pending"`. Clients poll
`GET /api/v1/investigations/{id}` for `status`, `progress_step`,
`error_message` and `updated_at`.

## Status transitions

```
pending ──claim──► processing ──► completed   (progress_step = "analysis_unavailable")
                        │
                        └───────► failed      (progress_step = step that failed,
                                               error_message = sanitized text)
```

- **Claim:** `UPDATE ... SET status='processing' WHERE id=:id AND status='pending'`.
  Exactly one task can claim an investigation; anything else is skipped.
- **Guarded writes:** every later update (progress, completion, failure) uses
  `WHERE id=:id AND status='processing'`. If the investigation is no longer
  processing, the write is skipped and `stale_update_skipped` is logged, so a
  stale task can never overwrite `completed` or `failed`.
- **Completed does not mean assessed.** No analysis exists yet: `risk_category`
  stays NULL and `progress_step` is `analysis_unavailable`. The UI says the
  message has not been assessed and must not be assumed safe.

## Steps

| step | purpose |
|---|---|
| `validating_submission` | Checks the investigation has at least one message; otherwise fails with "No message content was submitted." |
| `preparing_analysis` | Placeholder. OCR, URL scanning and LLM steps will be added after it. |

To add a step, append `ProcessingStep("<name>", <function(db, investigation_id)>)`
to `PROCESSING_STEPS`, and add a label for it in
`frontend/src/features/investigations/progressSteps.ts` (unknown step names
are shown as-is, so the UI never breaks). Names must fit `VARCHAR(64)`; no
migration is needed.

`PROCESSING_STEP_DELAY_SECONDS` (0–10, default 0) adds a pause before each
step so progress is visible during development.

## Sessions and transactions

- The task receives only the **investigation id and a session factory**. It
  never receives the request-scoped Session or ORM objects; the request
  session is closed once the response is sent.
- The task opens its own session. Each progress change is its own short
  transaction (commit per update), so other sessions see it immediately.
- On any exception the task's session is closed (rolling back uncommitted
  work) and the investigation is marked failed in a **fresh** session.

## Failure handling and logging

- `ProcessingError(safe_message)` is for expected problems; its fixed text is
  stored in `error_message`. Any other exception stores the generic
  "Processing failed due to an internal error. Please try again later."
- Exception text, tracebacks and submitted message content are **never**
  stored or logged. Logs (`app.services.processing`) contain only the
  investigation id, step name, exception class and SQLSTATE.
- The task never raises into the server.

## Limitations

1. **Not durable.** BackgroundTasks run inside the API process. If uvicorn
   stops or reloads (including `--reload` on file changes) mid-task, the
   investigation stays `processing`. The UI pauses polling after 5 minutes so
   this is visible. A future milestone may add a startup sweep or a job queue.
2. **If marking failed also fails** (e.g. the database is down), the
   investigation stays `processing`; the failure is logged as metadata.
3. **Threadpool use.** Tasks (and any configured delay) occupy a threadpool
   thread. The delay is capped at 10 seconds and defaults to 0.
4. **Logs contain investigation UUIDs.** Without authentication a UUID gives
   access to that investigation, so logs must be treated as private (see
   `security-notes.md`).
