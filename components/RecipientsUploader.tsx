"use client";

import { useRef, useState } from "react";
import { UploadCloud, ClipboardPaste } from "lucide-react";
import { parsePlainEmailList, parseRecipientsCsv } from "@/lib/csv";
import type { Recipient } from "@/types";

export function RecipientsUploader({
  onParsed,
}: {
  onParsed: (recipients: Recipient[]) => void;
}) {
  const [pasteText, setPasteText] = useState("");
  const [mode, setMode] = useState<"paste" | "csv">("paste");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function handlePasteSubmit() {
    if (!pasteText.trim()) return;
    onParsed(parsePlainEmailList(pasteText));
  }

  async function handleFile(file: File) {
    setFileName(file.name);
    const text = await file.text();
    onParsed(parseRecipientsCsv(text));
  }

  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card">
      <div className="mb-4 flex items-center gap-2">
        <TabButton active={mode === "paste"} onClick={() => setMode("paste")}>
          Paste addresses
        </TabButton>
        <TabButton active={mode === "csv"} onClick={() => setMode("csv")}>
          Upload CSV
        </TabButton>
      </div>

      {mode === "paste" ? (
        <div>
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder={"hr1@company.com\ncareers@abc.com\njobs@xyz.com"}
            rows={6}
            className="focus-ring w-full resize-none rounded-xl border border-ink-500 bg-ink-900 p-3 font-mono text-sm text-ink-100 placeholder:text-ink-400"
          />
          <button
            onClick={handlePasteSubmit}
            className="focus-ring mt-3 flex items-center gap-1.5 rounded-full bg-seal px-4 py-2 text-sm font-medium text-ink-900 transition hover:bg-seal-light"
          >
            <ClipboardPaste size={14} /> Load addresses
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files?.[0];
            if (f) handleFile(f);
          }}
          onClick={() => fileInputRef.current?.click()}
          className="focus-ring flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-ink-500 bg-ink-900/60 px-4 py-10 text-center transition hover:border-seal/60"
        >
          <UploadCloud size={22} className="text-ink-300" />
          <p className="text-sm text-ink-200">
            Drop a CSV here, or click to browse
          </p>
          <p className="font-mono text-xs text-ink-400">
            columns: Email, Name, Company, Position, Gender
          </p>
          {fileName && (
            <p className="mt-1 text-xs text-seal">{fileName} loaded</p>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
        </div>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`focus-ring rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
        active
          ? "bg-seal text-ink-900"
          : "border border-ink-500 text-ink-300 hover:text-ink-100"
      }`}
    >
      {children}
    </button>
  );
}
