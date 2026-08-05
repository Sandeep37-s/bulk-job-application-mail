"use client";

import { useMemo } from "react";
import type { Recipient, SendJobItem } from "@/types";
import { resolveGreeting } from "@/lib/gender";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export function RecipientsTable({
  recipients,
  jobItems,
}: {
  recipients: Recipient[];
  jobItems?: SendJobItem[];
}) {
  const validCount = recipients.filter((r) => r.valid).length;
  const invalidCount = recipients.length - validCount;

  const statusByEmail = useMemo(() => {
    const map = new Map<string, SendJobItem>();
    jobItems?.forEach((item) => map.set(item.recipient.email.toLowerCase(), item));
    return map;
  }, [jobItems]);

  if (recipients.length === 0) return null;

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 shadow-card">
      <div className="flex items-center justify-between border-b border-ink-600/70 px-5 py-3">
        <p className="font-display text-sm italic text-ink-100">
          {recipients.length} recipients parsed
        </p>
        <div className="flex items-center gap-3 font-mono text-xs">
          <span className="text-ok">{validCount} valid</span>
          {invalidCount > 0 && <span className="text-err">{invalidCount} skipped</span>}
        </div>
      </div>
      <div className="max-h-80 overflow-y-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-ink-800 text-xs uppercase tracking-wide text-ink-400">
            <tr>
              <th className="px-5 py-2 font-normal">Recipient</th>
              <th className="px-5 py-2 font-normal">Greeting</th>
              <th className="px-5 py-2 font-normal">Status</th>
            </tr>
          </thead>
          <tbody>
            {recipients.map((r) => {
              const greeting = r.valid
                ? resolveGreeting({
                    explicitGender: r.gender,
                    contactName: r.contactName,
                    name: r.name,
                  })
                : null;
              const job = statusByEmail.get(r.email.toLowerCase());
              return (
                <tr key={r.id} className="border-t border-ink-700/70">
                  <td className="px-5 py-2.5">
                    <p className="text-ink-100">{r.email}</p>
                    {r.name && <p className="text-xs text-ink-400">{r.name}</p>}
                  </td>
                  <td className="px-5 py-2.5 text-ink-300">
                    {greeting ? (
                      <span
                        title={`source: ${greeting.source} (${greeting.confidence} confidence)`}
                      >
                        {greeting.text}
                      </span>
                    ) : (
                      <span className="text-ink-500">—</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5">
                    <StatusBadge recipient={r} job={job} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ recipient, job }: { recipient: Recipient; job?: SendJobItem }) {
  if (!recipient.valid) {
    return (
      <span className="flex items-center gap-1 text-xs text-err">
        <XCircle size={13} /> {recipient.invalidReason}
      </span>
    );
  }
  if (!job || job.status === "pending") {
    return <span className="text-xs text-ink-400">Ready</span>;
  }
  if (job.status === "sending") {
    return <span className="text-xs text-seal">Sending…</span>;
  }
  if (job.status === "sent") {
    return (
      <span className="flex items-center gap-1 text-xs text-ok">
        <CheckCircle2 size={13} /> Sent
      </span>
    );
  }
  if (job.status === "failed") {
    return (
      <span className="flex items-center gap-1 text-xs text-err" title={job.error}>
        <AlertTriangle size={13} /> Failed
      </span>
    );
  }
  return <span className="text-xs text-ink-400">Skipped</span>;
}
