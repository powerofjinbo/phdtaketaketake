import Link from "next/link";
import { LogoMark } from "@/components/Nav";
import { IconHeart } from "@/components/Icons";

export default function SiteFooter() {
  return (
    <footer className="relative z-10 mt-auto px-6 pb-10 pt-16">
      <div className="mx-auto max-w-6xl">
        <div className="h-px w-full bg-gradient-to-r from-transparent via-white/15 to-transparent" />
        <div className="mt-8 flex flex-col items-center justify-between gap-6 text-sm text-zinc-500 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <LogoMark className="h-6 w-6" />
            <span className="text-zinc-400">
              PhDTake · every claim cited, nothing guessed
            </span>
          </div>
          <p className="flex items-center gap-2 text-center text-zinc-500">
            <IconHeart className="h-3.5 w-3.5 text-rose-300/80" />
            <span>
              Made for everyone drafting a cold email at 2 a.m.
              <span className="mx-1.5 text-zinc-700">·</span>
              <span className="text-zinc-400">献给每一个深夜还在改套磁信的你</span>
            </span>
          </p>
          <nav className="flex gap-4">
            <Link href="/settings" className="transition-colors hover:text-zinc-200">
              Key
            </Link>
            <Link href="/profile" className="transition-colors hover:text-zinc-200">
              Profile
            </Link>
            <Link href="/dashboard" className="transition-colors hover:text-zinc-200">
              Match
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
