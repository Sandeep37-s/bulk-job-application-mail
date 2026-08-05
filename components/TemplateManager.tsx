"use client";

import { useAppStore } from "@/lib/store";
import type { Template } from "@/types";
import { Trash2, FileText } from "lucide-react";

export function TemplateManager({ onLoad }: { onLoad: (t: Template) => void }) {
  const templates = useAppStore((s) => s.templates);
  const deleteTemplate = useAppStore((s) => s.deleteTemplate);

  if (templates.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-ink-600 p-5 text-center text-sm text-ink-400">
        No saved templates yet. Write a letter and save it to reuse later.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card">
      <p className="mb-3 font-display text-sm italic text-ink-100">Saved templates</p>
      <div className="flex flex-col gap-2">
        {templates.map((t) => (
          <div
            key={t.id}
            className="group flex items-center justify-between rounded-xl border border-ink-700 bg-ink-900/60 px-3 py-2.5"
          >
            <button
              onClick={() => onLoad(t)}
              className="focus-ring flex flex-1 items-center gap-2 text-left"
            >
              <FileText size={14} className="shrink-0 text-seal" />
              <span className="truncate text-sm text-ink-100">{t.name}</span>
            </button>
            <button
              onClick={() => deleteTemplate(t.id)}
              className="focus-ring text-ink-500 opacity-0 transition hover:text-err group-hover:opacity-100"
              aria-label={`Delete ${t.name}`}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
