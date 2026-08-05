"use client";

import { useState } from "react";
import { Save } from "lucide-react";
import { useAppStore } from "@/lib/store";

const VARIABLES = ["{{name}}", "{{company}}", "{{position}}"];

export function TemplateEditor({
  subject,
  body,
  onSubjectChange,
  onBodyChange,
}: {
  subject: string;
  body: string;
  onSubjectChange: (v: string) => void;
  onBodyChange: (v: string) => void;
}) {
  const addTemplate = useAppStore((s) => s.addTemplate);
  const [templateName, setTemplateName] = useState("");
  const [saved, setSaved] = useState(false);

  function insertVariable(variable: string) {
    onBodyChange(`${body}${body.endsWith(" ") || body.length === 0 ? "" : " "}${variable}`);
  }

  function handleSave() {
    if (!templateName.trim()) return;
    addTemplate({ name: templateName.trim(), subject, body });
    setSaved(true);
    setTemplateName("");
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card">
      <p className="mb-3 font-display text-sm italic text-ink-100">Your letter</p>

      <label className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-ink-400">
        Subject
      </label>
      <input
        value={subject}
        onChange={(e) => onSubjectChange(e.target.value)}
        placeholder="Application for AI/ML Engineer Position"
        className="focus-ring mb-4 w-full rounded-lg border border-ink-500 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-400"
      />

      <div className="mb-1 flex items-center justify-between">
        <label className="block font-mono text-[10px] uppercase tracking-wider text-ink-400">
          Body
        </label>
        <span className="text-[11px] text-ink-400">
          Greeting is added automatically — start your message after it
        </span>
      </div>
      <textarea
        value={body}
        onChange={(e) => onBodyChange(e.target.value)}
        rows={10}
        placeholder={"I hope you are doing well.\n\nI am writing to apply for the {{position}} position at {{company}}. Please find my resume attached.\n\nThank you for your time.\n\nRegards,\nSandeep Kumar"}
        className="focus-ring w-full resize-none rounded-lg border border-ink-500 bg-ink-900 p-3 text-sm leading-relaxed text-ink-100 placeholder:text-ink-400"
      />

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink-400">
          Insert:
        </span>
        {VARIABLES.map((v) => (
          <button
            key={v}
            onClick={() => insertVariable(v)}
            className="focus-ring rounded-full border border-ink-500 px-2.5 py-1 font-mono text-xs text-seal transition hover:border-seal"
          >
            {v}
          </button>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-ink-700/70 pt-4">
        <input
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
          placeholder="Save as template… (e.g. AI Engineer)"
          className="focus-ring flex-1 rounded-lg border border-ink-500 bg-ink-900 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-400"
        />
        <button
          onClick={handleSave}
          className="focus-ring flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-ink-500 px-3 py-2 text-sm text-ink-200 transition hover:border-seal hover:text-seal"
        >
          <Save size={14} /> {saved ? "Saved!" : "Save"}
        </button>
      </div>
    </div>
  );
}
