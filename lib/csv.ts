import Papa from "papaparse";
import type { Recipient } from "@/types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function normalizeHeader(h: string): string {
  return h.trim().toLowerCase().replace(/[^a-z]/g, "");
}

const HEADER_MAP: Record<string, keyof Recipient | "gender" | "contactName"> = {
  email: "email",
  emailaddress: "email",
  name: "name",
  fullname: "name",
  company: "company",
  companyname: "company",
  position: "position",
  role: "position",
  jobtitle: "position",
  gender: "gender",
  companycontactname: "contactName",
  contactname: "contactName",
};

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `r_${Date.now()}_${idCounter}`;
}

/** Parse a CSV file's raw text into structured, validated recipients. */
export function parseRecipientsCsv(csvText: string): Recipient[] {
  const result = Papa.parse<Record<string, string>>(csvText.trim(), {
    header: true,
    skipEmptyLines: true,
    transformHeader: (h) => h,
  });

  const rows = result.data;
  const recipients: Recipient[] = rows.map((row) => {
    const mapped: Partial<Recipient> = {};
    for (const [rawHeader, rawValue] of Object.entries(row)) {
      const key = HEADER_MAP[normalizeHeader(rawHeader)];
      if (!key) continue;
      const value = (rawValue ?? "").toString().trim();
      if (!value) continue;
      (mapped as any)[key] = value;
    }
    return buildRecipient(mapped.email, mapped);
  });

  return dedupeAndValidate(recipients);
}

/** Parse plain "one email per line" pasted text into recipients. */
export function parsePlainEmailList(text: string): Recipient[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    // allow a header line like "Email" to be pasted along with the list
    .filter((l) => normalizeHeader(l) !== "email");

  const recipients = lines.map((email) => buildRecipient(email, { email }));
  return dedupeAndValidate(recipients);
}

function buildRecipient(email: string | undefined, extra: Partial<Recipient>): Recipient {
  const cleanEmail = (email ?? "").trim();
  return {
    id: nextId(),
    email: cleanEmail,
    name: extra.name,
    company: extra.company,
    position: extra.position,
    gender: (extra as any).gender,
    contactName: (extra as any).contactName,
    valid: true,
  };
}

function dedupeAndValidate(recipients: Recipient[]): Recipient[] {
  const seen = new Set<string>();
  return recipients.map((r) => {
    const email = r.email.toLowerCase();
    let valid = true;
    let invalidReason: string | undefined;
    let duplicate = false;

    if (!email) {
      valid = false;
      invalidReason = "Empty row";
    } else if (!EMAIL_RE.test(email)) {
      valid = false;
      invalidReason = "Invalid email format";
    } else if (seen.has(email)) {
      duplicate = true;
      valid = false;
      invalidReason = "Duplicate email";
    } else {
      seen.add(email);
    }

    return { ...r, valid, invalidReason, duplicate };
  });
}

/** Replace {{variable}} placeholders in a template string with recipient data. */
export function applyVariables(
  template: string,
  recipient: Recipient,
  extra?: Record<string, string>
): string {
  const values: Record<string, string> = {
    name: recipient.name ?? "there",
    company: recipient.company ?? "your company",
    position: recipient.position ?? "the role",
    email: recipient.email,
    ...extra,
  };
  return template.replace(/{{\s*(\w+)\s*}}/g, (match, key) => {
    return values[key] !== undefined ? values[key] : match;
  });
}
