import Link from "next/link";

const features = [
  {
    title: "Connection-first CAPEG scoring",
    body: "Your advisor's network, lab pedigree, and letters are scored ahead of raw metrics — because that is how committees actually read applications. Signal flows to where it matters, not where it is easiest to count.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" stroke="currentColor" strokeWidth={1.6}>
        <circle cx="6" cy="6" r="2.5" />
        <circle cx="18" cy="6" r="2.5" />
        <circle cx="12" cy="18" r="2.5" />
        <path d="M7.8 7.8l3 7.2M16.2 7.8l-3 7.2M8.5 6h7" />
      </svg>
    ),
  },
  {
    title: "Evidence-cited research agent",
    body: "A research agent reads primary sources for every candidate advisor. Every signal it uses is cited; anything it cannot verify is flagged, never invented — intelligence, not guesswork.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" stroke="currentColor" strokeWidth={1.6}>
        <path d="M4 5a2 2 0 012-2h9l5 5v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
        <path d="M14 3v5h5M8 13h8M8 17h5" />
      </svg>
    ),
  },
  {
    title: "In-browser scoring engine",
    body: "Missing or blocked sources widen the confidence band instead of being guessed, so rankings expose the lower bound. The engine itself runs in your browser (Python via Pyodide) — your data never leaves this device.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" stroke="currentColor" strokeWidth={1.6}>
        <path d="M4 19h16M6 16V9M11 16V5M16 16v-6M21 16v-3" strokeLinecap="round" />
      </svg>
    ),
  },
];

const flowPoints = [
  { k: "Flow", v: "not friction" },
  { k: "Intelligence", v: "not complexity" },
  { k: "Movement", v: "not stagnation" },
  { k: "Scale", v: "not effort" },
];

export default function Home() {
  return (
    <div className="relative overflow-hidden">
      <section className="relative mx-auto max-w-4xl px-6 pt-28 pb-16 text-center">
        <p className="animate-fade-up mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-4 py-1 text-xs font-medium tracking-wide text-indigo-200 backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.9)]" />
          Built for physics, materials, and beyond
        </p>
        <h1 className="animate-fade-up delay-100 text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
          Truth-based PhD advisor matching —{" "}
          <span className="metal-text">every claim cited, nothing guessed</span>
        </h1>
        <p className="animate-fade-up delay-200 mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-zinc-300/90">
          PhDTake turns your application into a current of verified signal that
          flows through a connected intelligence network — scored against real
          advisors at real programs on a transparent 4.0 scale, with uncertainty
          shown, not hidden.
        </p>

        {/* Flow / intelligence / movement / scale */}
        <div className="animate-fade-up delay-300 mx-auto mt-8 flex max-w-2xl flex-wrap items-center justify-center gap-2.5">
          {flowPoints.map((p) => (
            <span
              key={p.k}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1.5 text-xs text-zinc-300 backdrop-blur"
            >
              <span className="font-medium text-white">{p.k}</span>{" "}
              <span className="text-zinc-500">{p.v}</span>
            </span>
          ))}
        </div>

        <div className="animate-fade-up delay-300 mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/settings"
            className="btn-primary rounded-xl px-6 py-3 font-medium"
          >
            Get your match report
          </Link>
          <Link href="/dashboard" className="btn-ghost rounded-xl px-6 py-3 font-medium">
            Open dashboard
          </Link>
        </div>
        <p className="animate-fade-up delay-400 mt-4 text-sm text-zinc-400">
          No signup. No server. Your API key stays in your browser.
        </p>
      </section>

      <section className="relative mx-auto max-w-6xl px-6 pb-28">
        <div className="grid gap-6 md:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="glass-card animate-fade-up delay-200 group rounded-2xl p-6"
            >
              <div className="metal-fill mb-4 inline-flex rounded-xl p-3 text-white/90 shadow-[0_0_20px_rgba(99,102,241,0.35)]">
                {f.icon}
              </div>
              <h3 className="mb-2 text-lg font-semibold text-white">
                {f.title}
              </h3>
              <p className="text-sm leading-relaxed text-zinc-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
