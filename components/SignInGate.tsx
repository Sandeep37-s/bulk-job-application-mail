"use client";

import { signIn } from "next-auth/react";
import { FileStack, ShieldCheck, Timer, ScrollText } from "lucide-react";

const POINTS = [
  {
    icon: ShieldCheck,
    title: "Sent from your own Gmail",
    body: "OAuth 2.0 with the gmail.send scope only — we never see or store your password, and mail leaves from your real address.",
  },
  {
    icon: FileStack,
    title: "One template, many recipients",
    body: "Paste addresses or upload a CSV with name, company, and position columns. Variables fill in automatically.",
  },
  {
    icon: ScrollText,
    title: "Careful greetings",
    body: "Sir/Madam is only used when your data says so with confidence. Otherwise it's Dear Hiring Manager — never a guess.",
  },
  {
    icon: Timer,
    title: "Paced sending",
    body: "Configurable delay between sends and a running daily count keep you comfortably under Gmail's limits.",
  },
];

export function SignInGate() {
  return (
    <div className="mx-auto flex max-w-6xl flex-col items-center px-6 pb-24 pt-20 text-center">
      <span className="rounded-full border border-seal/30 bg-seal/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.2em] text-seal">
        Your Gmail. Your applications.
      </span>
      <h1 className="mt-6 max-w-2xl font-display text-4xl italic leading-tight text-ink-50 sm:text-5xl">
        Send every job application like it took you all morning —
        <span className="text-seal not-italic"> in one click.</span>
      </h1>
      <p className="mt-5 max-w-xl text-balance text-sm text-ink-300 sm:text-base">
        Write the letter once. Dispatch personalizes the greeting, subject, and
        body for each recruiter, attaches your resume, and sends it — paced —
        straight from your own Gmail account.
      </p>
      <button
        onClick={() => signIn("google")}
        className="focus-ring mt-8 rounded-full bg-seal px-6 py-3 text-sm font-medium text-ink-900 shadow-card transition hover:bg-seal-light"
      >
        Sign in with Google to begin
      </button>

      <div className="mt-20 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-2">
        {POINTS.map(({ icon: Icon, title, body }) => (
          <div
            key={title}
            className="rounded-2xl border border-ink-600/70 bg-ink-800/60 p-5 shadow-card"
          >
            <Icon size={18} className="text-seal" />
            <p className="mt-3 font-display text-base text-ink-100">{title}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-300">{body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
