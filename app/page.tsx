"use client";

import { useSession } from "next-auth/react";
import { TopBar } from "@/components/TopBar";
import { SignInGate } from "@/components/SignInGate";
import { Dashboard } from "@/components/Dashboard";

export default function HomePage() {
  const { status } = useSession();

  return (
    <>
      <TopBar />
      {status === "authenticated" ? <Dashboard /> : <SignInGate />}
    </>
  );
}
