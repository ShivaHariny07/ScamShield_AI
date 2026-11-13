# Security notes: development build

## Status: no authentication or access control

ScamShield AI does **not** implement authentication yet (as of Milestone 2).

- Investigation and message UUIDs are **resource identifiers only, never
  authentication credentials**. The fact that UUIDv4 values are hard to guess
  is not relied on as a security control.
- **Anyone who obtains an investigation UUID can read that investigation and
  its messages, and add messages to it.**
- Submitted messages may contain sensitive personal data (bank details, OTPs,
  phone numbers). Treat every environment running this build as private.

## Localhost only

Until authentication and access control exist, run everything on the local
machine only:

| component | command / setting |
|---|---|
| Backend | `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload` (never `--host 0.0.0.0`) |
| Frontend | `npm run dev` (Vite binds to `localhost` by default; do not pass `--host`) |
| CORS | `CORS_ALLOWED_ORIGINS` defaults to `["http://localhost:5173"]` |
| Database | Docker publishes port 5433. Narrowing it to `127.0.0.1` is a pending decision. |

Do not expose the API, frontend or database to a network, tunnel or the internet.

## Required before any public or shared deployment

- [ ] Authentication (user identity on every request).
- [ ] Access control: ownership checks on **every** investigation and message
      endpoint (`investigations.user_id` already exists for this).
- [ ] Rate limiting on submission endpoints.
- [ ] HTTPS / TLS termination.
- [ ] Production `CORS_ALLOWED_ORIGINS` limited to the real frontend origin.
- [ ] Database port not publicly reachable; credentials rotated from development values.
- [ ] Review of logging to make sure no submitted content or secrets are logged.

## Current safeguards (already in place)

- Request schemas reject unknown fields, so clients cannot set server-owned
  fields (`status`, `risk_category`, `user_id`, `role`, `assistant_response`).
- Clients can only create `user` messages; assistant content is server-only.
- Database errors return generic messages (503/500).
- Database errors are logged as metadata only (HTTP method, path, exception
  class, SQLSTATE and constraint name), never exception text or row data.
  The engine also uses `hide_parameters=True`.
- No update or delete endpoints exist; submitted evidence is preserved.
- The frontend renders submitted text as plain text (no HTML injection).
