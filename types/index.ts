export type Gender = "male" | "female" | "unknown";

export interface Recipient {
  id: string;
  email: string;
  name?: string;
  company?: string;
  position?: string;
  gender?: string; // raw value from CSV, e.g. "M", "Female", "Mr"
  contactName?: string; // explicit "Company Contact Name" column
  valid: boolean;
  invalidReason?: string;
  duplicate?: boolean;
}

export type GreetingSource =
  | "explicit-gender"
  | "contact-name"
  | "name-inference"
  | "fallback";

export interface ResolvedGreeting {
  text: string; // e.g. "Dear Hiring Manager,"
  source: GreetingSource;
  confidence: "high" | "medium" | "low";
}

export interface Template {
  id: string;
  name: string;
  subject: string;
  body: string;
  createdAt: string;
  updatedAt: string;
}

export interface AttachmentMeta {
  id: string;
  filename: string;
  mimeType: string;
  base64: string; // raw base64 content, no data: prefix
  sizeBytes: number;
  kind: "resume" | "extra";
}

export type SendStatus = "pending" | "sending" | "sent" | "failed" | "skipped";

export interface SendJobItem {
  recipient: Recipient;
  subject: string;
  body: string;
  greeting: ResolvedGreeting;
  status: SendStatus;
  error?: string;
  messageId?: string;
  sentAt?: string;
  overridden?: boolean;
}

export interface HistoryEntry {
  id: string;
  recipientEmail: string;
  recipientName?: string;
  subject: string;
  status: "sent" | "failed";
  error?: string;
  date: string;
  templateName?: string;
}

export interface DailyUsage {
  date: string; // yyyy-mm-dd
  count: number;
}
