import { apiRequest } from "./client";

// Mirrors backend/app/models/enums.py and backend/app/schemas/*.py
export type SubmissionType = "text" | "screenshot" | "url" | "mixed";
export type IncidentType =
  | "suspicious_message_only"
  | "clicked_link"
  | "entered_credentials"
  | "shared_otp"
  | "transferred_money";
export type RiskCategory = "unknown" | "low" | "medium" | "high" | "critical";
export type InvestigationStatus = "pending" | "processing" | "completed" | "failed";
export type UserSourceType = "typed_text" | "pasted_text" | "image_ocr";

export const MAX_TEXT_LENGTH = 20_000;

export interface MessageCreate {
  original_text?: string;
  ocr_text?: string;
  submission_source_type?: UserSourceType;
  detected_language?: string;
}

export interface InvestigationCreate {
  submission_type: SubmissionType;
  incident_type?: IncidentType | null;
  initial_message?: MessageCreate;
}

export interface Investigation {
  id: string;
  submission_type: SubmissionType;
  incident_type: IncidentType | null;
  risk_category: RiskCategory | null;
  status: InvestigationStatus;
  progress_step: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export function createInvestigation(payload: InvestigationCreate): Promise<Investigation> {
  return apiRequest<Investigation>("/api/v1/investigations", {
    method: "POST",
    body: payload,
  });
}

export function getInvestigation(id: string, signal?: AbortSignal): Promise<Investigation> {
  return apiRequest<Investigation>(`/api/v1/investigations/${encodeURIComponent(id)}`, {
    signal,
  });
}

/** Statuses after which background processing will not change anything. */
export const TERMINAL_STATUSES: readonly InvestigationStatus[] = ["completed", "failed"];

export function isTerminal(status: InvestigationStatus): boolean {
  return TERMINAL_STATUSES.includes(status);
}
