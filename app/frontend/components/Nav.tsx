"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";
import { clearToken, getToken } from "@/lib/api";

function subscribeToAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener("phdtake-auth", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("phdtake-auth", callback);
  };
}

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const authed = useSyncExternalStore(
    subscribeToAuth,
    () => !!getToken(),
    () => false
  );

  function logout() {
    clearToken();
    router.push("/login");
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
          {authed ? (
            <>
              <Link href="/dashboard" className={linkCls("/dashboard")}>
                Dashboard
              </Link>
              <Link href="/profile" className={linkCls("/profile")}>
                Profile
              </Link>
              <Link href="/settings" className={linkCls("/settings")}>
                Settings
              </Link>
              <button
                onClick={logout}
                className="ml-2 rounded-md border border-white/10 px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:border-white/25 hover:text-zinc-100"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className={linkCls("/login")}>
                Log in
              </Link>
              <Link
                href="/register"
                className="ml-2 rounded-md bg-gradient-to-r from-indigo-500 to-violet-600 px-3 py-1.5 text-sm font-medium text-white shadow-[0_0_16px_rgba(99,102,241,0.35)] transition-opacity hover:opacity-90"
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
