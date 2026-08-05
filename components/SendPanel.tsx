"use client";

import { useMemo, useRef, useState } from "react";
import { Send, RotateCcw, Beaker } from "lucide-react";
import { useSession } from "next-auth/react";
import { useAppStore } from "@/lib/store";
import type { SendJobItem } from "@/types";

const DELAY_OPTIONS = [2, 5, 10];

export function SendPanel({
  jobItems,
  setJobItems,
}: {
  jobItems: SendJobItem[];
  setJobItems: (items: SendJobItem[]) => void;
}) {
  const { data: session } = useSession();
  const delaySeconds = useAppStore((s) => s.delaySeconds);
  const setDelaySeconds = useAppStore((s) => s.setDelaySeconds);
  const dailyLimit = useAppStore((s) => s.dailyLimit);
  const recordSend = useAppStore((s) => s.recordSend);
  const todaysCount = useAppStore((s) => s.todaysCount);
  const resume = useAppStore((s) => s.resume);
  const extraAttachments = useAppStore((s) => s.extraAttachments);

  const [isSending, setIsSending] = useState(false);
  const stopRequestedRef = useRef(false);
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  const counts = useMemo(() => {
    const sent = jobItems.filter((i) => i.status === "sent").length;
    const failed = jobItems.filter((i) => i.status === "failed").length;
    const pending = jobItems.filter((i) => i.status === "pending").length;
    return { sent, failed, pending, total: jobItems.length };
  }, [jobItems]);

  const usedToday = todaysCount();
  const projectedTotal = usedToday + counts.pending;
  const overLimit = projectedTotal > dailyLimit;

  async function sendOne(item: SendJobItem): Promise<{ ok: boolean; patch: Partial<SendJobItem> }> {
    try {
      const attachments = [
        ...(resume
          ? [{ filename: resume.filename, mimeType: resume.mimeType, base64: resume.base64 }]
          : []),
        ...extraAttachments.map((a) => ({
          filename: a.filename,
          mimeType: a.mimeType,
          base64: a.base64,
        })),
      ];

      const res = await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: item.recipient.email,
          subject: item.subject,
          body: item.body,
          attachments,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        recordSend({
          recipientEmail: item.recipient.email,
          recipientName: item.recipient.name,
          subject: item.subject,
          status: "failed",
          error: data.error,
        });
        return { ok: false, patch: { status: "failed", error: data.error ?? "Send failed" } };
      }

      recordSend({
        recipientEmail: item.recipient.email,
        recipientName: item.recipient.name,
        subject: item.subject,
        status: "sent",
      });
      return {
        ok: true,
        patch: { status: "sent", messageId: data.messageId, sentAt: new Date().toISOString() },
      };
    } catch (err: any) {
      recordSend({
        recipientEmail: item.recipient.email,
        recipientName: item.recipient.name,
        subject: item.subject,
        status: "failed",
        error: err?.message,
      });
      return { ok: false, patch: { status: "failed", error: err?.message ?? "Network error" } };
    }
  }

  async function sendBatch(targetStatuses: SendJobItem["status"][]) {
    setIsSending(true);
    stopRequestedRef.current = false;

    // Local mutable copy so limit checks and progress stay accurate across
    // the whole run, independent of React's async state updates.
    const working = [...jobItems];
    let sentThisRun = 0;
    let stopped = false;

    for (let i = 0; i < working.length; i++) {
      if (stopRequestedRef.current) {
        stopped = true;
        break;
      }
      const current = working[i];
      if (!targetStatuses.includes(current.status)) continue;

      if (usedToday + sentThisRun >= dailyLimit) {
        stopped = true;
        break;
      }

      working[i] = { ...current, status: "sending" };
      setJobItems([...working]);

      const { ok, patch } = await sendOne(current);
      working[i] = { ...working[i], ...patch };
      if (ok) sentThisRun += 1;
      setJobItems([...working]);

      if (i < working.length - 1) {
        await new Promise((r) => setTimeout(r, delaySeconds * 1000));
      }
    }

    if (stopped) setJobItems([...working]);
    setIsSending(false);
  }

  async function handleSendTest() {
    if (!session?.user?.email || jobItems.length === 0) return;
    setTestSending(true);
    setTestResult(null);
    const sample = jobItems[0];
    try {
      const attachments = [
        ...(resume
          ? [{ filename: resume.filename, mimeType: resume.mimeType, base64: resume.base64 }]
          : []),
      ];
      const res = await fetch("/api/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: session.user.email,
          subject: `[TEST] ${sample.subject}`,
          body: sample.body,
          attachments,
        }),
      });
      const data = await res.json();
      setTestResult(res.ok ? "Test email sent to your inbox." : `Failed: ${data.error}`);
    } catch (err: any) {
      setTestResult(`Failed: ${err?.message ?? "network error"}`);
    } finally {
      setTestSending(false);
    }
  }

  const progressPct = counts.total ? Math.round(((counts.sent + counts.failed) / counts.total) * 100) : 0;

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <p className="font-display text-sm italic text-ink-100">Send</p>
        <div className="font-mono text-xs text-ink-300">
          Today&rsquo;s sent{" "}
          <span className={overLimit ? "text-err" : "text-seal"}>
            {usedToday} / {dailyLimit}
          </span>
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-400">
          Delay between sends
        </span>
        <div className="flex gap-1">
          {DELAY_OPTIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDelaySeconds(d)}
              className={`focus-ring rounded-full px-2.5 py-1 text-xs transition ${
                delaySeconds === d
                  ? "bg-seal text-ink-900"
                  : "border border-ink-500 text-ink-300"
              }`}
            >
              {d}s
            </button>
          ))}
        </div>
      </div>

      {overLimit && (
        <p className="mb-3 rounded-lg border border-err/40 bg-err/10 px-3 py-2 text-xs text-err">
          Sending all pending emails would take you to {projectedTotal} today, above your
          limit of {dailyLimit}. Some sends will be held back automatically.
        </p>
      )}

      {counts.total > 0 && (
        <div className="mb-4">
          <div className="mb-1 flex justify-between font-mono text-xs text-ink-400">
            <span>
              {counts.sent} sent · {counts.failed} failed · {counts.pending} pending
            </span>
            <span>{progressPct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
            <div
              className="h-full rounded-full bg-seal transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          disabled={isSending || counts.pending === 0}
          onClick={() => sendBatch(["pending"])}
          className="focus-ring flex items-center gap-1.5 rounded-full bg-seal px-4 py-2 text-sm font-medium text-ink-900 transition hover:bg-seal-light disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={14} />
          {isSending ? "Sending…" : `Send ${counts.pending} email${counts.pending === 1 ? "" : "s"}`}
        </button>

        {isSending && (
          <button
            onClick={() => {
              stopRequestedRef.current = true;
            }}
            className="focus-ring rounded-full border border-ink-500 px-4 py-2 text-sm text-ink-200 hover:border-err hover:text-err"
          >
            Stop
          </button>
        )}

        {counts.failed > 0 && !isSending && (
          <button
            onClick={() => sendBatch(["failed"])}
            className="focus-ring flex items-center gap-1.5 rounded-full border border-ink-500 px-4 py-2 text-sm text-ink-200 hover:border-seal hover:text-seal"
          >
            <RotateCcw size={14} /> Retry {counts.failed} failed
          </button>
        )}

        <button
          disabled={testSending || jobItems.length === 0}
          onClick={handleSendTest}
          className="focus-ring flex items-center gap-1.5 rounded-full border border-ink-500 px-4 py-2 text-sm text-ink-200 hover:border-seal hover:text-seal disabled:opacity-40"
        >
          <Beaker size={14} /> {testSending ? "Sending test…" : "Send test to myself"}
        </button>
      </div>
      {testResult && <p className="mt-2 text-xs text-ink-300">{testResult}</p>}
    </div>
  );
}
