const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

const NETWORK_ERROR =
  "Could not reach the ScamShield AI server. Please check that the backend is running.";
const GENERIC_ERROR = "Something went wrong. Please try again.";

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

const FIELD_LABELS: Record<string, string> = {
  original_text: "Message",
  ocr_text: "Extracted text",
  incident_type: "Incident type",
  submission_type: "Submission type",
  submission_source_type: "Message source",
  detected_language: "Language",
};

/** Turn FastAPI's 422 detail list into one readable sentence. */
function formatValidationError(issues: ValidationIssue[]): string {
  const first = issues[0];
  if (!first?.msg) return "The submitted data is invalid.";

  const message = first.msg.replace(/^Value error,\s*/, "");
  const field = first.loc?.[first.loc.length - 1];
  const label = typeof field === "string" ? FIELD_LABELS[field] : undefined;
  return label ? `${label}: ${message}` : message;
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let detail: unknown;
  try {
    detail = ((await response.json()) as { detail?: unknown }).detail;
  } catch {
    detail = undefined;
  }

  if (response.status === 422 && Array.isArray(detail)) {
    return new ApiError(formatValidationError(detail as ValidationIssue[]), 422);
  }
  if (typeof detail === "string" && detail.length > 0) {
    return new ApiError(detail, response.status);
  }
  return new ApiError(GENERIC_ERROR, response.status);
}

export async function apiRequest<T>(
  path: string,
  options: { method?: "GET" | "POST"; body?: unknown } = {},
): Promise<T> {
  const { method = "GET", body } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(NETWORK_ERROR, null);
  }

  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return (await response.json()) as T;
}
