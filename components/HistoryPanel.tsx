"use client";

import { useMemo, useState } from "react";
import { Search, Trash2, CheckCircle2, XCircle, Download } from "lucide-react";
import { useAppStore } from "@/lib/store";

function downloadCsv(rows: { recipientEmail: string; subject: string; status: string; date: string; error?: string }[]) {
  const header = ["Recipient", "Subject", "Status", "Date", "Error"];
  const lines = rows.map((r) =>
    [r.recipientEmail, r.subject, r.status, r.date, r.error ?? ""]
      .map((v) => `"${String(v).replace(/"/g, '""')}"`)
      .join(",")
  );
  const csv = [header.join(","), ...lines].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sending-report-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function HistoryPanel() {
  const history = useAppStore((s) => s.history);
  const clearHistory = useAppStore((s) => s.clearHistory);
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return history;
    return history.filter(
      (h) =>
        h.recipientEmail.toLowerCase().includes(q) ||
        h.subject.toLowerCase().includes(q) ||
        (h.recipientName ?? "").toLowerCase().includes(q)
    );
  }, [history, query]);

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 shadow-card">
      <div className="flex items-center justify-between gap-3 border-b border-ink-600/70 px-5 py-3">
        <p className="font-display text-sm italic text-ink-100">Send history</p>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full border border-ink-600 bg-ink-900 px-3 py-1.5">
            <Search size={12} className="text-ink-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search history…"
              className="focus-ring w-32 bg-transparent text-xs text-ink-100 placeholder:text-ink-500 sm:w-48"
            />
          </div>
          {history.length > 0 && (
            <>
              <button
                onClick={() => downloadCsv(filtered)}
                className="focus-ring text-ink-400 hover:text-seal"
                aria-label="Download report"
                title="Download CSV report"
              >
                <Download size={14} />
              </button>
              <button
                onClick={clearHistory}
                className="focus-ring text-ink-500 hover:text-err"
                aria-label="Clear history"
              >
                <Trash2 size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-ink-400">
          {history.length === 0 ? "No emails sent yet." : "No matches."}
        </p>
      ) : (
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-ink-800 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-5 py-2 font-normal">Recipient</th>
                <th className="px-5 py-2 font-normal">Subject</th>
                <th className="px-5 py-2 font-normal">Date</th>
                <th className="px-5 py-2 font-normal">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((h) => (
                <tr key={h.id} className="border-t border-ink-700/70">
                  <td className="px-5 py-2.5 text-ink-100">{h.recipientEmail}</td>
                  <td className="max-w-[220px] truncate px-5 py-2.5 text-ink-300">
                    {h.subject}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-ink-400">
                    {new Date(h.date).toLocaleString()}
                  </td>
                  <td className="px-5 py-2.5">
                    {h.status === "sent" ? (
                      <span className="flex items-center gap-1 text-xs text-ok">
                        <CheckCircle2 size={13} /> Sent
                      </span>
                    ) : (
                      <span
                        className="flex items-center gap-1 text-xs text-err"
                        title={h.error}
                      >
                        <XCircle size={13} /> Failed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
