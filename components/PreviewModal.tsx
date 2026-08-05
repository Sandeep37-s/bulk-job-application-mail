"use client";

import { useState } from "react";
import { X, ChevronLeft, ChevronRight, Paperclip } from "lucide-react";
import type { SendJobItem } from "@/types";
import { useAppStore } from "@/lib/store";

export function PreviewModal({
  items,
  initialIndex,
  onClose,
  onSave,
}: {
  items: SendJobItem[];
  initialIndex: number;
  onClose: () => void;
  onSave: (index: number, patch: { subject: string; body: string; greetingText: string }) => void;
}) {
  const [index, setIndex] = useState(initialIndex);
  const item = items[index];
  const resume = useAppStore((s) => s.resume);
  const extraAttachments = useAppStore((s) => s.extraAttachments);

  const [subject, setSubject] = useState(item.subject);
  const [body, setBody] = useState(item.body);

  function go(delta: number) {
    const next = index + delta;
    if (next < 0 || next >= items.length) return;
    onSave(index, { subject, body, greetingText: item.greeting.text });
    setIndex(next);
    setSubject(items[next].subject);
    setBody(items[next].body);
  }

  function handleClose() {
    onSave(index, { subject, body, greetingText: item.greeting.text });
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-8">
      <div className="flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-ink-600 bg-ink-800 shadow-card">
        <div className="flex items-center justify-between border-b border-ink-700 px-5 py-3">
          <div>
            <p className="font-display text-sm italic text-ink-100">Preview</p>
            <p className="font-mono text-xs text-ink-400">
              {index + 1} of {items.length} · {item.recipient.email}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => go(-1)}
              disabled={index === 0}
              className="focus-ring rounded-full p-1.5 text-ink-300 hover:text-seal disabled:opacity-30"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => go(1)}
              disabled={index === items.length - 1}
              className="focus-ring rounded-full p-1.5 text-ink-300 hover:text-seal disabled:opacity-30"
            >
              <ChevronRight size={16} />
            </button>
            <button
              onClick={handleClose}
              className="focus-ring ml-1 rounded-full p-1.5 text-ink-300 hover:text-err"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          <div className="mb-3 rounded-lg border border-ink-700 bg-ink-900/60 p-3 font-mono text-xs text-ink-300">
            <p>
              <span className="text-ink-500">To:</span> {item.recipient.email}
            </p>
            <p className="mt-0.5">
              <span className="text-ink-500">Greeting source:</span>{" "}
              {item.greeting.source} ({item.greeting.confidence} confidence)
            </p>
          </div>

          <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-400">
            Subject
          </label>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="focus-ring mb-4 w-full rounded-lg border border-ink-500 bg-ink-900 px-3 py-2 text-sm text-ink-100"
          />

          <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-400">
            Body
          </label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={12}
            className="focus-ring w-full resize-none rounded-lg border border-ink-500 bg-ink-900 p-3 text-sm leading-relaxed text-ink-100"
          />

          {(resume || extraAttachments.length > 0) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {resume && (
                <span className="flex items-center gap-1 rounded-full border border-ink-600 px-2.5 py-1 text-xs text-ink-300">
                  <Paperclip size={11} className="text-seal" /> {resume.filename}
                </span>
              )}
              {extraAttachments.map((a) => (
                <span
                  key={a.id}
                  className="flex items-center gap-1 rounded-full border border-ink-600 px-2.5 py-1 text-xs text-ink-300"
                >
                  <Paperclip size={11} /> {a.filename}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
