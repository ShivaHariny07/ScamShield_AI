import type { IncidentType } from "../../api/investigations";

export const INCIDENT_TYPE_OPTIONS: { value: IncidentType; label: string }[] = [
  { value: "suspicious_message_only", label: "I only received a suspicious message" },
  { value: "clicked_link", label: "I clicked a link in the message" },
  { value: "entered_credentials", label: "I entered my password or card details" },
  { value: "shared_otp", label: "I shared an OTP or verification code" },
  { value: "transferred_money", label: "I transferred money" },
];
