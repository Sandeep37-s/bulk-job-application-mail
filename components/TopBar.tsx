"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { Mail, LogOut } from "lucide-react";
import Image from "next/image";

export function TopBar() {
  const { data: session, status } = useSession();

  return (
    <header className="sticky top-0 z-30 border-b border-ink-600/60 bg-ink-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-seal/15 text-seal">
            <Mail size={16} strokeWidth={2.2} />
          </div>
          <div className="leading-tight">
            <p className="font-display text-lg italic text-ink-100">Dispatch</p>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-300">
              bulk job-application mail
            </p>
          </div>
        </div>

        {status === "authenticated" && session?.user ? (
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-ink-500 bg-ink-800 py-1 pl-1 pr-3 sm:flex">
              {session.user.image ? (
                <Image
                  src={session.user.image}
                  alt=""
                  width={24}
                  height={24}
                  className="rounded-full"
                />
              ) : null}
              <span className="text-xs text-ink-200">{session.user.email}</span>
            </div>
            <button
              onClick={() => signOut()}
              className="focus-ring flex items-center gap-1.5 rounded-full border border-ink-500 px-3 py-1.5 text-xs text-ink-200 transition hover:border-wax hover:text-wax"
            >
              <LogOut size={13} /> Sign out
            </button>
          </div>
        ) : status === "loading" ? (
          <div className="h-8 w-24 animate-pulse rounded-full bg-ink-700" />
        ) : (
          <button
            onClick={() => signIn("google")}
            className="focus-ring rounded-full bg-seal px-4 py-2 text-sm font-medium text-ink-900 transition hover:bg-seal-light"
          >
            Sign in with Google
          </button>
        )}
      </div>
    </header>
  );
}
