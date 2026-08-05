"use client";

import { useMemo, useState } from "react";
import { Eye, Settings2 } from "lucide-react";
import { RecipientsUploader } from "./RecipientsUploader";
import { RecipientsTable } from "./RecipientsTable";
import { TemplateEditor } from "./TemplateEditor";
import { TemplateManager } from "./TemplateManager";
import { AttachmentUploader } from "./AttachmentUploader";
import { PreviewModal } from "./PreviewModal";
import { SendPanel } from "./SendPanel";
import { HistoryPanel } from "./HistoryPanel";
import { buildJobItems } from "@/lib/jobs";
import { useAppStore } from "@/lib/store";
import type { Recipient, SendJobItem, Template } from "@/types";

export function Dashboard() {
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [subject, setSubject] = useState("Application for AI/ML Engineer Position");
  const [body, setBody] = useState(
    "I hope you are doing well.\n\nI am writing to apply for the {{position}} position at {{company}}. Please find my resume attached.\n\nThank you for your time.\n\nRegards,\nSandeep Kumar"
  );
  const [jobItems, setJobItems] = useState<SendJobItem[]>([]);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const dailyLimit = useAppStore((s) => s.dailyLimit);
  const setDailyLimit = useAppStore((s) => s.setDailyLimit);

  const validRecipients = useMemo(() => recipients.filter((r) => r.valid), [recipients]);

  function handleParsed(parsed: Recipient[]) {
    setRecipients(parsed);
    setJobItems(buildJobItems(parsed, subject, body));
  }

  function handleBuildPreview() {
    setJobItems(buildJobItems(recipients, subject, body));
    setPreviewIndex(0);
  }

  function handleLoadTemplate(t: Template) {
    setSubject(t.subject);
    setBody(t.body);
    if (recipients.length > 0) {
      setJobItems(buildJobItems(recipients, t.subject, t.body));
    }
  }

  function handlePreviewSave(
    index: number,
    patch: { subject: string; body: string; greetingText: string }
  ) {
    setJobItems((prev) =>
      prev.map((item, i) =>
        i === index
          ? {
              ...item,
              subject: patch.subject,
              body: patch.body,
              overridden: true,
            }
          : item
      )
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 pb-24 pt-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl italic text-ink-50">Compose &amp; send</h1>
          <p className="mt-1 text-sm text-ink-300">
            One letter, personalized for every recruiter on your list.
          </p>
        </div>
        <button
          onClick={() => setShowSettings((s) => !s)}
          className="focus-ring flex items-center gap-1.5 rounded-full border border-ink-500 px-3 py-1.5 text-xs text-ink-300 hover:border-seal hover:text-seal"
        >
          <Settings2 size={13} /> Limits
        </button>
      </div>

      {showSettings && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-ink-600 bg-ink-800/60 px-4 py-3">
          <label className="font-mono text-xs uppercase tracking-wider text-ink-400">
            Gmail daily send limit
          </label>
          <input
            type="number"
            min={1}
            value={dailyLimit}
            onChange={(e) => setDailyLimit(Math.max(1, Number(e.target.value) || 1))}
            className="focus-ring w-24 rounded-lg border border-ink-500 bg-ink-900 px-2 py-1 text-sm text-ink-100"
          />
          <p className="text-xs text-ink-400">
            Free Gmail accounts allow roughly 500 sends/day; Workspace accounts vary by plan.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col gap-6">
          <RecipientsUploader onParsed={handleParsed} />
          <RecipientsTable recipients={recipients} jobItems={jobItems} />
          <AttachmentUploader />
        </div>

        <div className="flex flex-col gap-6">
          <TemplateEditor
            subject={subject}
            body={body}
            onSubjectChange={setSubject}
            onBodyChange={setBody}
          />
          <TemplateManager onLoad={handleLoadTemplate} />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col gap-3">
          <button
            onClick={handleBuildPreview}
            disabled={validRecipients.length === 0}
            className="focus-ring flex items-center justify-center gap-2 rounded-xl border border-ink-500 bg-ink-800/60 px-4 py-3 text-sm text-ink-200 transition hover:border-seal hover:text-seal disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Eye size={15} /> Preview &amp; edit before sending
          </button>
        </div>
        <SendPanel jobItems={jobItems} setJobItems={setJobItems} />
      </div>

      <div className="mt-6">
        <HistoryPanel />
      </div>

      {previewIndex !== null && jobItems.length > 0 && (
        <PreviewModal
          items={jobItems}
          initialIndex={previewIndex}
          onClose={() => setPreviewIndex(null)}
          onSave={handlePreviewSave}
        />
      )}
    </div>
  );
}
