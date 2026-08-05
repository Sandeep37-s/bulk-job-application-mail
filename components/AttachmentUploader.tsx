"use client";

import { useRef } from "react";
import { Paperclip, FileUp, X } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { fileToBase64, formatBytes } from "@/lib/file";
import type { AttachmentMeta } from "@/types";

function uid() {
  return `att_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function AttachmentUploader() {
  const resume = useAppStore((s) => s.resume);
  const setResume = useAppStore((s) => s.setResume);
  const extraAttachments = useAppStore((s) => s.extraAttachments);
  const addExtraAttachment = useAppStore((s) => s.addExtraAttachment);
  const removeExtraAttachment = useAppStore((s) => s.removeExtraAttachment);

  const resumeInputRef = useRef<HTMLInputElement>(null);
  const extraInputRef = useRef<HTMLInputElement>(null);

  async function handleResumeSelect(file: File) {
    const base64 = await fileToBase64(file);
    const meta: AttachmentMeta = {
      id: uid(),
      filename: file.name,
      mimeType: file.type || "application/pdf",
      base64,
      sizeBytes: file.size,
      kind: "resume",
    };
    setResume(meta);
  }

  async function handleExtraSelect(files: FileList) {
    for (const file of Array.from(files)) {
      const base64 = await fileToBase64(file);
      addExtraAttachment({
        id: uid(),
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        base64,
        sizeBytes: file.size,
        kind: "extra",
      });
    }
  }

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card">
      <p className="mb-3 font-display text-sm italic text-ink-100">Attachments</p>

      {/* Resume */}
      <div className="mb-3">
        <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-400">
          Resume (attached to every email)
        </label>
        {resume ? (
          <div className="flex items-center justify-between rounded-lg border border-ink-700 bg-ink-900/60 px-3 py-2">
            <span className="flex items-center gap-2 truncate text-sm text-ink-100">
              <Paperclip size={13} className="text-seal" /> {resume.filename}
              <span className="text-xs text-ink-400">{formatBytes(resume.sizeBytes)}</span>
            </span>
            <button
              onClick={() => setResume(null)}
              className="focus-ring text-ink-500 hover:text-err"
              aria-label="Remove resume"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => resumeInputRef.current?.click()}
            className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-ink-600 py-4 text-sm text-ink-300 transition hover:border-seal/60"
          >
            <FileUp size={15} /> Upload resume (PDF)
          </button>
        )}
        <input
          ref={resumeInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleResumeSelect(f);
          }}
        />
      </div>

      {/* Extra attachments */}
      <div>
        <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-400">
          Additional attachments (cover letter, certificates, portfolio)
        </label>
        <div className="flex flex-col gap-1.5">
          {extraAttachments.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-ink-700 bg-ink-900/60 px-3 py-2"
            >
              <span className="flex items-center gap-2 truncate text-sm text-ink-100">
                <Paperclip size={13} className="text-ink-300" /> {a.filename}
                <span className="text-xs text-ink-400">{formatBytes(a.sizeBytes)}</span>
              </span>
              <button
                onClick={() => removeExtraAttachment(a.id)}
                className="focus-ring text-ink-500 hover:text-err"
                aria-label={`Remove ${a.filename}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={() => extraInputRef.current?.click()}
          className="focus-ring mt-1.5 flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-ink-600 py-3 text-xs text-ink-300 transition hover:border-seal/60"
        >
          <FileUp size={13} /> Add file
        </button>
        <input
          ref={extraInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleExtraSelect(e.target.files);
          }}
        />
      </div>
    </div>
  );
}
