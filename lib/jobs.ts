import type { Recipient, SendJobItem } from "@/types";
import { resolveGreeting } from "@/lib/gender";
import { applyVariables } from "@/lib/csv";

export function buildJobItems(
  recipients: Recipient[],
  subjectTemplate: string,
  bodyTemplate: string
): SendJobItem[] {
  return recipients
    .filter((r) => r.valid)
    .map((recipient) => {
      const greeting = resolveGreeting({
        explicitGender: recipient.gender,
        contactName: recipient.contactName,
        name: recipient.name,
      });
      const subject = applyVariables(subjectTemplate, recipient);
      const bodyWithGreeting = bodyTemplate.includes("{{greeting}}")
        ? applyVariables(bodyTemplate, recipient, { greeting: greeting.text })
        : `${greeting.text}\n\n${applyVariables(bodyTemplate, recipient)}`;

      return {
        recipient,
        subject,
        body: bodyWithGreeting,
        greeting,
        status: "pending" as const,
      };
    });
}
