"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const pathname = usePathname();

  const linkCls = (href: string) =>
    `rounded-md px-3 py-1.5 text-sm transition-colors ${
      pathname === href || pathname.startsWith(href + "/")
        ? "bg-indigo-500/15 text-indigo-200"
        : "text-zinc-400 hover:text-zinc-100 hover:bg-white/5"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#07070c]/55 backdrop-blur-xl backdrop-saturate-150 supports-[backdrop-filter]:bg-[#07070c]/45">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="group flex items-center gap-2">
          <span className="metal-fill relative inline-block h-6 w-6 rounded-md shadow-[0_0_18px_rgba(99,102,241,0.55)] transition-transform duration-300 group-hover:scale-110">
            <span className="absolute inset-0 rounded-md bg-white/20 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
          </span>
          <span className="text-lg font-semibold tracking-tight text-white">
            PhD<span className="metal-text">Take</span>
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
        </nav>
      </div>
    </header>
  );
}
