import Link from "next/link";
import ConstellationHero from "@/components/ConstellationHero";
import Reveal from "@/components/Reveal";
import Typewriter from "@/components/Typewriter";
import {
  IconArrow,
  IconChart,
  IconCompass,
  IconDoc,
  IconHeart,
  IconKey,
  IconNetwork,
  IconShield,
  IconUser,
} from "@/components/Icons";

const FIELDS = [
  "condensed matter",
  "materials science",
  "quantum information",
  "machine learning",
  "biophysics",
  "chemistry",
];

const principles = [
  {
    Icon: IconNetwork,
    kicker: "Connection-first",
    title: "Who you know, verified",
    body: "Your current advisor's real network — co-authors, lab lineage, shared grants — is weighted ahead of raw prestige, because that is how committees actually read applications.",
  },
  {
    Icon: IconDoc,
    kicker: "Evidence-first",
    title: "Every claim has a source",
    body: "A research agent reads primary sources for each candidate. Anything it cannot verify is flagged as missing or blocked — never filled in with a guess.",
  },
  {
    Icon: IconShield,
    kicker: "Private by design",
    title: "Nothing leaves your browser",
    body: "The scoring engine is Python running in your browser via Pyodide. No account, no server, no database. Your key and your profile stay on this device.",
  },
];

const legend = [
  {
    dot: "bg-cyan-300 shadow-[0_0_10px_rgba(103,232,249,0.9)]",
    line: "border-cyan-300/70",
    name: "Verified",
    body: "Found in a source we actually fetched. Counts toward your score.",
  },
  {
    dot: "bg-zinc-500",
    line: "border-dashed border-zinc-500/70",
    name: "Missing",
    body: "Not found. Widens the confidence band instead of being guessed.",
  },
  {
    dot: "bg-amber-300",
    line: "border-dashed border-amber-300/70",
    name: "Blocked",
    body: "Source unreachable. Marked honestly so you know what to check.",
  },
];

const steps = [
  {
    Icon: IconKey,
    href: "/settings",
    title: "Bring a key",
    body: "Paste any LLM API key. Gemini's is free.",
  },
  {
    Icon: IconUser,
    href: "/profile",
    title: "Tell your story",
    body: "Fill your profile, or drop in your CV and let it prefill.",
  },
  {
    Icon: IconCompass,
    href: "/dashboard",
    title: "Get your map",
    body: "A ranked, cited list of advisors, with a strategy for each.",
  },
];

const pipeline = [
  { k: "Match", v: "CAPEG pillars, connection weighted highest" },
  { k: "Strength", v: "plus live opportunity signals" },
  { k: "Risk", v: "minus half the uncertainty band" },
  { k: "Difficulty", v: "minus the program's selectivity" },
  { k: "Strategy", v: "priority · target · reach" },
];

export default function Home() {
  return (
    <div className="relative overflow-x-clip">
      {/* ---------------- Hero ---------------- */}
      <section className="relative mx-auto grid max-w-6xl items-center gap-6 px-6 pb-10 pt-14 sm:pt-20 lg:grid-cols-[1.05fr_1fr] lg:gap-10">
        <div className="text-center lg:text-left">
          <p className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-zinc-300 backdrop-blur">
            <span className="relative flex h-2 w-2">
              <span className="pulse-ring absolute inline-flex h-full w-full rounded-full bg-cyan-300" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-300" />
            </span>
            PhD advisor matching for{" "}
            <Typewriter words={FIELDS} className="font-mono text-cyan-200" />
          </p>

          <h1 className="animate-fade-up delay-100 mt-7 text-[2.6rem] font-semibold leading-[1.05] tracking-tight text-white sm:text-6xl lg:text-[4.1rem]">
            Find the advisor who is{" "}
            <span className="font-display italic font-normal text-[1.08em] ember-text pr-1">
              already
            </span>{" "}
            <span className="metal-text">one connection away.</span>
          </h1>

          <p className="animate-fade-up delay-200 mx-auto mt-6 max-w-xl text-lg leading-relaxed text-zinc-300/90 lg:mx-0">
            PhDTake maps the real academic network around you, scores every
            candidate advisor on a transparent 4.0 scale, and shows its work.
            Every claim cited. Nothing guessed.
          </p>

          <div className="animate-fade-up delay-300 mt-9 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
            <Link href="/settings" className="btn-primary group rounded-xl px-6 py-3 font-medium">
              Start your match
              <IconArrow className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
            <Link href="/dashboard" className="btn-ghost rounded-xl px-6 py-3 font-medium">
              Open dashboard
            </Link>
          </div>
          <p className="animate-fade-up delay-400 mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-sm text-zinc-500 lg:justify-start">
            <span>No signup</span>
            <span className="h-1 w-1 rounded-full bg-zinc-700" />
            <span>No server</span>
            <span className="h-1 w-1 rounded-full bg-zinc-700" />
            <span>Free with a Gemini key</span>
          </p>
        </div>

        <div className="animate-fade-up delay-200 mx-auto w-full max-w-[520px]">
          <ConstellationHero className="aspect-square w-full" />
        </div>
      </section>

      {/* ---------------- Legend ---------------- */}
      <section className="relative mx-auto max-w-6xl px-6">
        <Reveal>
          <div className="glass grid gap-px overflow-hidden rounded-2xl sm:grid-cols-3">
            {legend.map((l) => (
              <div key={l.name} className="flex items-start gap-4 bg-black/10 p-5">
                <span className="mt-2 flex shrink-0 items-center">
                  <span className={`h-2.5 w-2.5 rounded-full ${l.dot}`} />
                  <span className={`w-7 border-t-2 ${l.line}`} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{l.name}</p>
                  <p className="mt-1 text-sm leading-relaxed text-zinc-400">{l.body}</p>
                </div>
              </div>
            ))}
          </div>
        </Reveal>
      </section>

      {/* ---------------- Principles ---------------- */}
      <section className="relative mx-auto max-w-6xl px-6 pt-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="eyebrow">What makes it different</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Built on how admissions{" "}
            <span className="font-display italic font-normal text-[1.1em] text-indigo-200">
              really
            </span>{" "}
            work
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {principles.map((p, i) => (
            <Reveal key={p.title} delay={i * 120}>
              <div className="glass-card spotlight group h-full rounded-2xl p-7">
                <div className="flex items-center gap-3">
                  <span className="metal-fill inline-flex rounded-xl p-2.5 text-white shadow-[0_0_24px_rgba(99,102,241,0.35)] transition-transform duration-500 group-hover:-rotate-6 group-hover:scale-110">
                    <p.Icon className="h-5 w-5" />
                  </span>
                  <span className="eyebrow">{p.kicker}</span>
                </div>
                <h3 className="mt-5 text-xl font-semibold text-white">{p.title}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-zinc-400">{p.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- Pipeline ---------------- */}
      <section className="relative mx-auto max-w-6xl px-6 pt-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="eyebrow">Transparent scoring</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            Five layers. No black box.
          </h2>
          <p className="mt-4 text-zinc-400">
            Each layer composes the one before it, and every number traces back
            to evidence. The result is a relative-fit index, never a fake
            admission probability.
          </p>
        </Reveal>
        <Reveal delay={120}>
          <ol className="relative mt-12 grid gap-3 md:grid-cols-5">
            <span
              aria-hidden="true"
              className="absolute left-[10%] right-[10%] top-6 hidden h-px bg-gradient-to-r from-indigo-400/0 via-indigo-300/50 to-cyan-300/0 md:block"
            />
            {pipeline.map((s, i) => (
              <li key={s.k} className="relative flex items-center gap-4 md:flex-col md:text-center">
                <span className="glass relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl font-mono text-sm text-indigo-200">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="font-semibold text-white md:mt-3">{s.k}</p>
                  <p className="mt-0.5 text-sm text-zinc-400">{s.v}</p>
                </div>
              </li>
            ))}
          </ol>
        </Reveal>
      </section>

      {/* ---------------- How it works ---------------- */}
      <section className="relative mx-auto max-w-6xl px-6 pt-28">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="eyebrow">Three steps, about ten minutes</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
            From a blank page to a plan
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 120}>
              <Link
                href={s.href}
                className="glass-card spotlight group flex h-full flex-col rounded-2xl p-7"
              >
                <div className="flex items-center justify-between">
                  <span className="font-display text-5xl italic text-white/20 transition-colors duration-500 group-hover:text-indigo-200/60">
                    {i + 1}
                  </span>
                  <span className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-indigo-200">
                    <s.Icon className="h-5 w-5" />
                  </span>
                </div>
                <h3 className="mt-6 text-lg font-semibold text-white">{s.title}</h3>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-zinc-400">{s.body}</p>
                <span className="mt-5 inline-flex items-center gap-1.5 text-sm text-indigo-300 transition-colors group-hover:text-white">
                  Go
                  <IconArrow className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-1" />
                </span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------------- A note ---------------- */}
      <section className="relative mx-auto max-w-3xl px-6 pb-8 pt-28">
        <Reveal>
          <div className="glass-strong aurora-border relative overflow-hidden rounded-3xl px-7 py-12 text-center sm:px-14">
            <div
              aria-hidden="true"
              className="absolute -top-24 left-1/2 h-48 w-72 -translate-x-1/2 rounded-full bg-amber-300/10 blur-3xl"
            />
            <IconHeart className="mx-auto h-6 w-6 text-rose-300" />
            <p className="font-display mx-auto mt-5 max-w-xl text-2xl italic leading-snug text-zinc-100 sm:text-[1.7rem]">
              Applying to a PhD is lonely work. You deserve a map that is honest
              about what it knows, and about what it doesn&apos;t.
            </p>
            <p className="mx-auto mt-5 max-w-lg text-sm leading-relaxed text-zinc-400">
              申请博士是一段孤独的路。愿这张地图诚实地告诉你它知道什么、不知道什么，
              陪你找到那位真正适合你的导师。
            </p>
            <Link href="/settings" className="btn-primary group mt-8 rounded-xl px-6 py-3 font-medium">
              Begin
              <IconArrow className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
            <p className="mt-6 flex items-center justify-center gap-2 text-xs text-zinc-500">
              <IconChart className="h-3.5 w-3.5" />
              A 4.0-scale relative fit index, not an admission probability.
            </p>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
