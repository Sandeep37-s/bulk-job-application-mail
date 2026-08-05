import type { Gender, GreetingSource, ResolvedGreeting } from "@/types";

/**
 * IMPORTANT LIMITATION
 * ---------------------------------------------------------------------------
 * There is no reliable way to determine a person's gender from an email
 * address or a first name alone. Names are shared across genders and
 * cultures, and any name-based heuristic will be wrong for some people.
 *
 * This module therefore treats name-based inference as a LOW-CONFIDENCE
 * signal only. Unless the CSV explicitly provides a "Gender" column or a
 * "Company Contact Name" that resolves to a clear honorific, the app will
 * always fall back to a neutral greeting ("Dear Hiring Manager," /
 * "Dear Recruitment Team,"). It will never guess "Sir" or "Madam" purely
 * from an email address.
 *
 * The name list below is intentionally small and illustrative (common,
 * unambiguous first names), not exhaustive. It exists only to catch the
 * clearest cases; everything else safely falls through to neutral.
 */

const CLEARLY_MASCULINE = new Set([
  "james", "john", "robert", "michael", "david", "william", "richard",
  "joseph", "thomas", "rahul", "amit", "vijay", "arjun", "rohan", "karan",
  "raj", "sandeep", "ankit", "manish", "suresh", "ramesh", "vikram",
  "aditya", "abhishek", "gaurav", "nikhil", "pranav", "rajesh", "sanjay",
]);

const CLEARLY_FEMININE = new Set([
  "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan",
  "jessica", "sarah", "karen", "priya", "neha", "pooja", "anjali", "kavita",
  "sneha", "divya", "shreya", "ritu", "swati", "meera", "anita", "sunita",
  "nisha", "deepika", "kritika", "aishwarya",
]);

const NEUTRAL_FALLBACKS = ["Dear Hiring Manager,", "Dear Recruitment Team,"];

function extractFirstName(fullName?: string): string | null {
  if (!fullName) return null;
  const cleaned = fullName.trim().split(/\s+/)[0];
  if (!cleaned) return null;
  return cleaned.toLowerCase().replace(/[^a-z]/g, "");
}

/** Parse an explicit "Gender" column value like "M", "Male", "F", "Female". */
function parseExplicitGender(value?: string): Gender {
  if (!value) return "unknown";
  const v = value.trim().toLowerCase();
  if (["m", "male", "man", "mr"].includes(v)) return "male";
  if (["f", "female", "woman", "ms", "mrs", "miss"].includes(v)) return "female";
  return "unknown";
}

/** Try to pull an honorific from a free-text "Company Contact Name" field. */
function honorificFromContactName(contactName?: string): Gender {
  if (!contactName) return "unknown";
  const v = contactName.trim().toLowerCase();
  if (/^(mr\.?|mister)\s/.test(v)) return "male";
  if (/^(mrs\.?|ms\.?|miss|madam)\s/.test(v)) return "female";
  return "unknown";
}

function inferFromFirstName(name?: string): { gender: Gender; confidence: "high" | "medium" | "low" } {
  const first = extractFirstName(name);
  if (!first) return { gender: "unknown", confidence: "low" };
  if (CLEARLY_MASCULINE.has(first)) return { gender: "male", confidence: "medium" };
  if (CLEARLY_FEMININE.has(first)) return { gender: "female", confidence: "medium" };
  return { gender: "unknown", confidence: "low" };
}

let fallbackCursor = 0;
function nextNeutralGreeting(): string {
  const greeting = NEUTRAL_FALLBACKS[fallbackCursor % NEUTRAL_FALLBACKS.length];
  fallbackCursor += 1;
  return greeting;
}

export interface GenderInferenceInput {
  explicitGender?: string;
  contactName?: string;
  name?: string;
}

/**
 * Resolve the greeting line for a recipient using a strict priority order.
 * Never guesses "Sir"/"Madam" from low-confidence signals — anything below
 * medium confidence resolves to a neutral greeting.
 */
export function resolveGreeting(input: GenderInferenceInput): ResolvedGreeting {
  // 1. Explicit Gender column — highest trust, since the user supplied it directly.
  const explicit = parseExplicitGender(input.explicitGender);
  if (explicit !== "unknown") {
    return {
      text: explicit === "male" ? "Dear Sir," : "Dear Madam,",
      source: "explicit-gender" as GreetingSource,
      confidence: "high",
    };
  }

  // 2. Honorific embedded in an explicit "Company Contact Name" field.
  const honorific = honorificFromContactName(input.contactName);
  if (honorific !== "unknown") {
    return {
      text: honorific === "male" ? "Dear Sir," : "Dear Madam,",
      source: "contact-name" as GreetingSource,
      confidence: "high",
    };
  }
  if (input.contactName && input.contactName.trim()) {
    // We have a real contact name but no honorific — address them by name
    // rather than guessing gender.
    return {
      text: `Dear ${input.contactName.trim()},`,
      source: "contact-name" as GreetingSource,
      confidence: "high",
    };
  }

  // 3. Weak, name-based inference — only used at medium+ confidence.
  const inferred = inferFromFirstName(input.name);
  if (inferred.gender !== "unknown" && inferred.confidence !== "low") {
    return {
      text: inferred.gender === "male" ? "Dear Sir," : "Dear Madam,",
      source: "name-inference" as GreetingSource,
      confidence: inferred.confidence,
    };
  }

  // 4. Safe neutral fallback — alternates between two neutral phrasings.
  return {
    text: nextNeutralGreeting(),
    source: "fallback" as GreetingSource,
    confidence: "low",
  };
}
