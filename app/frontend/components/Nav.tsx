"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { loadProfile, loadSettings, onSetupChanged } from "@/lib/store";
import { IconCheck, IconCompass, IconKey, IconUser } from "@/components/Icons";

/** The logo mark: one bright node (you) wired to three advisors. */
export function LogoMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#a5b4fc" />
          <stop offset="0.55" stopColor="#c4b5fd" />
          <stop offset="1" stopColor="#67e8f9" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="9" fill="url(#logo-g)" opacity="0.14" />
      <rect x="1.5" y="1.5" width="29" height="29" rx="8.5" fill="none" stroke="url(#logo-g)" strokeOpacity="0.55" />
      <path d="M16 17.5L9 10M16 17.5L23.5 11M16 17.5V25" stroke="url(#logo-g)" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="9" cy="10" r="2.2" fill="#a5b4fc" />
      <circle cx="23.5" cy="11" r="2.2" fill="#67e8f9" />
      <circle cx="16" cy="25" r="2.2" fill="#c4b5fd" />
      <circle cx="16" cy="17.5" r="3.3" fill="#fbbf77" />
    </svg>
  );
}

const LINKS = [
  { href: "/settings", label: "Key", full: "API key", Icon: IconKey, step: "key" as const },
  { href: "/profile", label: "Profile", full: "Profile", Icon: IconUser, step: "profile" as const },
  { href: "/dashboard", label: "Match", full: "Match", Icon: IconCompass, step: null },
];

export default function Nav() {
  const pathname = usePathname();
  const [done, setDone] = useState({ key: false, profile: false });

  useEffect(() => {
    const check = () =>
      setDone({
        key: !!loadSettings()?.apiKey?.trim(),
        profile: !!loadProfile(),
      });
    const t = setTimeout(check, 0);
    const unsub = onSetupChanged(check);
    return () => {
      clearTimeout(t);
      unsub();
    };
  }, [pathname]);

  const isActive = (href: string) =>
    pathname === href ||
    pathname.startsWith(href + "/") ||
    (href === "/dashboard" && pathname.startsWith("/runs"));

  return (
    <header className="sticky top-0 z-40 px-3 pt-3 sm:px-6">
      <div className="glass mx-auto flex h-14 max-w-6xl items-center justify-between rounded-2xl pl-3 pr-2 sm:pl-4">
        <Link href="/" className="group flex items-center gap-2.5" aria-label="PhDTake home">
          <span className="transition-transform duration-500 group-hover:rotate-[18deg] group-hover:scale-110">
            <LogoMark />
          </span>
          <span className="text-[1.05rem] font-semibold tracking-tight text-white">
            PhD<span className="metal-text">Take</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1" aria-label="Main">
          {LINKS.map(({ href, label, full, Icon, step }, i) => {
            const active = isActive(href);
            const complete = step ? done[step] : false;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                title={full}
                className={`group relative flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm transition-all duration-300 sm:px-3 ${
                  active
                    ? "bg-white/[0.08] text-white shadow-[0_0_0_1px_rgba(165,180,252,0.25)_inset]"
                    : "text-zinc-400 hover:bg-white/[0.05] hover:text-zinc-100"
                }`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold transition-colors ${
                    complete
                      ? "bg-emerald-400/20 text-emerald-300"
                      : active
                        ? "bg-indigo-400/25 text-indigo-200"
                        : "bg-white/[0.06] text-zinc-500 group-hover:text-zinc-300"
                  }`}
                >
                  {complete ? <IconCheck className="h-3 w-3" /> : i + 1}
                </span>
                <Icon className="h-4 w-4 opacity-70 sm:hidden md:block" />
                <span className="hidden sm:inline">{label}</span>
                {active && (
                  <span className="absolute inset-x-3 -bottom-px h-px bg-gradient-to-r from-transparent via-indigo-300/80 to-transparent" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
