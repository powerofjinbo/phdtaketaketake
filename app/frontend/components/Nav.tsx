"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import { clearToken, getToken, isGuest } from "@/lib/api";

function subscribeToAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("phdtake-auth", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("phdtake-auth", callback);
  };
}

type Session = "none" | "guest" | "account";

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  // "account" = real login; guest tokens are minted silently as needed.
  const session = useSyncExternalStore<Session>(
    subscribeToAuth,
    () => (getToken() ? (isGuest() ? "guest" : "account") : "none"),
    () => "none"
  );

  function logout() {
    clearToken();
    router.push("/");
  }

  const linkCls = (href: string) =>
    `rounded-md px-3 py-1.5 text-sm transition-colors ${
      pathname === href || pathname.startsWith(href + "/")
        ? "bg-indigo-500/15 text-indigo-300"
        : "text-zinc-400 hover:text-zinc-100 hover:bg-white/5"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#09090f]/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="inline-block h-6 w-6 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 shadow-[0_0_16px_rgba(99,102,241,0.5)]" />
          <span className="text-lg font-semibold tracking-tight text-white">
            PhD<span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Take</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          <Link href="/dashboard" className={linkCls("/dashboard")}>
            Dashboard
          </Link>
          <Link href="/profile" className={linkCls("/profile")}>
            Profile
          </Link>
          <Link href="/settings" className={linkCls("/settings")}>
            Settings
          </Link>

          {session === "account" ? (
            <button
              onClick={logout}
              className="ml-2 rounded-md border border-white/10 px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:border-white/25 hover:text-zinc-100"
            >
              Log out
            </button>
          ) : (
            <>
              {session === "guest" && (
                <span
                  title="Your data lives in this browser. Create an account to keep it."
                  className="ml-2 inline-flex cursor-help items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-500/10 px-2.5 py-0.5 text-xs text-amber-300"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  Guest session
                </span>
              )}
              <Link
                href="/login"
                className="ml-2 text-sm text-zinc-500 transition-colors hover:text-zinc-200"
                title="Save your data across devices"
              >
                Log in
              </Link>
              <span className="text-zinc-700">/</span>
              <Link
                href="/register"
                className="text-sm text-zinc-500 transition-colors hover:text-zinc-200"
                title="Save your data across devices"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
