"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Template, HistoryEntry, AttachmentMeta } from "@/types";

function uid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

interface AppState {
  templates: Template[];
  history: HistoryEntry[];
  resume: AttachmentMeta | null;
  extraAttachments: AttachmentMeta[];
  delaySeconds: number;
  dailyLimit: number;
  usageByDate: Record<string, number>;

  addTemplate: (t: Omit<Template, "id" | "createdAt" | "updatedAt">) => Template;
  updateTemplate: (id: string, patch: Partial<Pick<Template, "name" | "subject" | "body">>) => void;
  deleteTemplate: (id: string) => void;

  setResume: (a: AttachmentMeta | null) => void;
  addExtraAttachment: (a: AttachmentMeta) => void;
  removeExtraAttachment: (id: string) => void;

  setDelaySeconds: (n: number) => void;
  setDailyLimit: (n: number) => void;

  recordSend: (entry: Omit<HistoryEntry, "id" | "date">) => void;
  todaysCount: () => number;
  clearHistory: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      templates: [],
      history: [],
      resume: null,
      extraAttachments: [],
      delaySeconds: 5,
      dailyLimit: 500,
      usageByDate: {},

      addTemplate: (t) => {
        const now = new Date().toISOString();
        const template: Template = { ...t, id: uid("tpl"), createdAt: now, updatedAt: now };
        set((s) => ({ templates: [template, ...s.templates] }));
        return template;
      },
      updateTemplate: (id, patch) => {
        set((s) => ({
          templates: s.templates.map((t) =>
            t.id === id ? { ...t, ...patch, updatedAt: new Date().toISOString() } : t
          ),
        }));
      },
      deleteTemplate: (id) => {
        set((s) => ({ templates: s.templates.filter((t) => t.id !== id) }));
      },

      setResume: (a) => set({ resume: a }),
      addExtraAttachment: (a) =>
        set((s) => ({ extraAttachments: [...s.extraAttachments, a] })),
      removeExtraAttachment: (id) =>
        set((s) => ({ extraAttachments: s.extraAttachments.filter((a) => a.id !== id) })),

      setDelaySeconds: (n) => set({ delaySeconds: n }),
      setDailyLimit: (n) => set({ dailyLimit: n }),

      recordSend: (entry) => {
        const date = new Date().toISOString();
        const historyEntry: HistoryEntry = { ...entry, id: uid("hist"), date };
        set((s) => {
          const key = todayKey();
          const nextUsage = { ...s.usageByDate };
          if (entry.status === "sent") {
            nextUsage[key] = (nextUsage[key] ?? 0) + 1;
          }
          return {
            history: [historyEntry, ...s.history].slice(0, 5000),
            usageByDate: nextUsage,
          };
        });
      },
      todaysCount: () => get().usageByDate[todayKey()] ?? 0,
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: "bulk-email-sender-storage",
      partialize: (s) => ({
        templates: s.templates,
        history: s.history,
        resume: s.resume,
        extraAttachments: s.extraAttachments,
        delaySeconds: s.delaySeconds,
        dailyLimit: s.dailyLimit,
        usageByDate: s.usageByDate,
      }),
    }
  )
);
