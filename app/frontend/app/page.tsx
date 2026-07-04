import Link from "next/link";

const features = [
  {
    title: "Connection-first CAPEG scoring",
    body: "Your advisor's network, lab pedigree, and letters are scored ahead of raw metrics — because that is how committees actually read applications.",
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
    body: "A research agent reads primary sources for every candidate advisor. Every signal it uses is cited; anything it cannot verify is flagged, never invented.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" stroke="currentColor" strokeWidth={1.6}>
        <path d="M4 5a2 2 0 012-2h9l5 5v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
        <path d="M14 3v5h5M8 13h8M8 17h5" />
      </svg>
    ),
  },
  {
    title: "Risk-adjusted rankings",
    body: "Missing or blocked sources widen the confidence band instead of being guessed. Rankings expose the lower bound, so you can plan for the worst case. The scoring engine itself runs in your browser (Python via Pyodide), so your data never leaves this device.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" stroke="currentColor" strokeWidth={1.6}>
        <path d="M4 19h16M6 16V9M11 16V5M16 16v-6M21 16v-3" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function Home() {
  return (
    <div className="relative overflow-hidden">
      {/* gradient orbs */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-indigo-600/20 blur-3xl animate-float-slow" />
      <div className="pointer-events-none absolute top-40 -left-40 h-96 w-96 rounded-full bg-violet-600/15 blur-3xl animate-float-slow" />
      <div className="pointer-events-none absolute top-96 -right-40 h-96 w-96 rounded-full bg-fuchsia-600/10 blur-3xl animate-float-slow" />

      <section className="relative mx-auto max-w-4xl px-6 pt-28 pb-20 text-center">
        <p className="animate-fade-up mb-6 inline-block rounded-full border border-indigo-400/30 bg-indigo-500/10 px-4 py-1 text-xs font-medium tracking-wide text-indigo-300">
          Built for physics, materials, and beyond
        </p>
        <h1 className="animate-fade-up delay-100 text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
          Truth-based PhD advisor matching —{" "}
          <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            every claim cited, nothing guessed
          </span>
        </h1>
        <p className="animate-fade-up delay-200 mx-auto mt-6 max-w-2xl text-lg text-zinc-400">
          PhDTake scores your application against real advisors at real programs
          on a transparent 4.0 scale — grounded in verifiable evidence, with
          uncertainty shown, not hidden.
        </p>
        <div className="animate-fade-up delay-300 mt-10 flex items-center justify-center gap-4">
          <Link
            href="/settings"
            className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-3 font-medium text-white shadow-[0_0_28px_rgba(99,102,241,0.45)] transition-transform hover:scale-[1.03]"
          >
            Get your match report
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg border border-white/15 px-6 py-3 font-medium text-zinc-300 transition-colors hover:border-white/30 hover:text-white"
          >
            Open dashboard
          </Link>
        </div>
        <p className="animate-fade-up delay-300 mt-4 text-sm text-zinc-500">
          No signup. No server. Your API key stays in your browser.
        </p>
      </section>

      <section className="relative mx-auto max-w-6xl px-6 pb-28">
        <div className="grid gap-6 md:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition-all hover:-translate-y-1 hover:border-indigo-400/40 hover:bg-indigo-500/[0.06] hover:shadow-[0_8px_40px_rgba(99,102,241,0.15)]"
            >
              <div className="mb-4 inline-flex rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-600/20 p-3 text-indigo-300">
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
