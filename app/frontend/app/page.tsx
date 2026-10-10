import Link from "next/link";
import NetworkGlobe from "@/components/NetworkGlobe";
import ConstellationHero from "@/components/ConstellationHero";
import Reveal from "@/components/Reveal";
import Typewriter from "@/components/Typewriter";
import { CountUp, EvidenceTerminal, ScoreDemo, ScrollPipeline } from "@/components/home/HomeWidgets";
import { IconArrow, IconHeart, IconKey, IconShield, IconCompass, IconUser } from "@/components/Icons";

const FIELDS = [
  "condensed matter",
  "materials science",
  "quantum information",
  "machine learning",
  "biophysics",
  "chemistry",
];

const MARQUEE_A = [
  "Condensed matter",
  "Quantum information",
  "Materials science",
  "Machine learning",
  "Biophysics",
  "Photonics",
  "Astrophysics",
  "Chemical engineering",
  "Neuroscience",
  "Robotics",
];
const MARQUEE_B = [
  "co-author verified",
  "lab lineage",
  "shared grant",
  "same research center",
  "committee member",
  "genealogy",
  "conference session",
  "co-mentored student",
];

/** Splits text into letters that rise in one after another. */
function Kinetic({
  text,
  start = 0,
  className = "",
  gradient,
}: {
  text: string;
  start?: number;
  className?: string;
  gradient?: [string, string];
}) {
  let i = 0;
  const total = text.replace(/ /g, "").length;
  // background-clip:text does not reach transformed children, so a gradient
  // is applied letter by letter instead.
  const mix = (k: number) => {
    if (!gradient) return undefined;
    const [a, b] = gradient.map((h) => [1, 3, 5].map((o) => parseInt(h.slice(o, o + 2), 16)));
    const t = total > 1 ? k / (total - 1) : 0;
    return `rgb(${a.map((v, n) => Math.round(v + (b[n] - v) * t)).join(",")})`;
  };
  return (
    <span className={className} aria-label={text}>
      {text.split(" ").map((word, wi) => (
        <span key={wi} className="inline-block whitespace-nowrap" aria-hidden="true">
          {word.split("").map((ch) => {
            const k = i++;
            const d = start + k * 28;
            return (
              <span key={d} className="letter-rise" style={{ animationDelay: `${d}ms`, color: mix(k) }}>
                {ch}
              </span>
            );
          })}
          {wi < text.split(" ").length - 1 && <span className="inline-block w-[0.28em]" />}
        </span>
      ))}
    </span>
  );
}

function MarqueeRow({ items, reverse = false, dur = "45s" }: { items: string[]; reverse?: boolean; dur?: string }) {
  const doubled = [...items, ...items];
  return (
    <div className="marquee-mask overflow-hidden">
      <div
        className={`marquee ${reverse ? "marquee-reverse" : ""}`}
        style={{ "--marquee-dur": dur } as React.CSSProperties}
      >
        {doubled.map((t, i) => (
          <span key={i} className="flex items-center gap-6 pr-6">
            <span className="whitespace-nowrap">{t}</span>
            <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-br from-indigo-300 to-cyan-300 opacity-60" />
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="relative overflow-x-clip">
      {/* ================= HERO ================= */}
      <section className="relative -mt-[4.25rem] flex min-h-[100svh] items-center pt-[4.25rem]">
        {/* rotating conic glow */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="spin-slow absolute left-1/2 top-1/2 h-[140vmax] w-[140vmax] -translate-x-1/2 -translate-y-1/2 bg-[conic-gradient(from_0deg,transparent_0deg,rgba(99,102,241,0.12)_60deg,transparent_120deg,rgba(34,211,238,0.08)_200deg,transparent_260deg,rgba(251,191,119,0.06)_320deg,transparent_360deg)]" />
        </div>

        <div className="relative mx-auto grid w-full max-w-7xl items-center gap-4 px-6 lg:grid-cols-[1.15fr_1fr]">
          <div className="relative z-10 order-2 text-center lg:order-1 lg:text-left">
            <p className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/[0.06] px-3.5 py-1.5 text-xs font-medium text-zinc-300 backdrop-blur">
              <span className="relative flex h-2 w-2">
                <span className="pulse-ring absolute inline-flex h-full w-full rounded-full bg-cyan-300" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-300" />
              </span>
              Advisor matching for <Typewriter words={FIELDS} className="font-mono text-cyan-200" />
            </p>

            <h1 className="mt-7 text-[2.9rem] font-semibold leading-[0.98] tracking-[-0.035em] text-white sm:text-7xl xl:text-[5rem]">
              <Kinetic text="Your next advisor" start={150} />
              <br />
              <Kinetic text="is already" start={650} className="text-zinc-400" />{" "}
              <span className="font-display font-normal italic tracking-normal">
                <Kinetic text="in your orbit." start={950} className="pr-2" gradient={["#fde68a", "#fb7185"]} />
              </span>
            </h1>

            <p className="animate-fade-up mx-auto mt-7 max-w-xl text-lg leading-relaxed text-zinc-300/90 lg:mx-0" style={{ animationDelay: "1.3s" }}>
              PhDTake maps the real academic network around you, finds the
              advisors you can actually reach, and scores each one on a
              transparent 4.0 scale.{" "}
              <span className="text-white">Every claim cited. Nothing guessed.</span>
            </p>

            <div className="animate-fade-up mt-9 flex flex-wrap items-center justify-center gap-3 lg:justify-start" style={{ animationDelay: "1.5s" }}>
              <Link href="/settings" className="btn-primary group rounded-2xl px-7 py-3.5 text-[1.02rem] font-medium">
                Map my network
                <IconArrow className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
              </Link>
              <Link href="/dashboard" className="btn-ghost rounded-2xl px-7 py-3.5 text-[1.02rem] font-medium">
                Open dashboard
              </Link>
            </div>

            <dl className="animate-fade-up mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-white/10 pt-6 text-left max-lg:mx-auto" style={{ animationDelay: "1.7s" }}>
              <div>
                <dt className="text-xs text-zinc-500">scoring layers</dt>
                <dd className="mt-1 font-mono text-2xl font-semibold text-white">
                  <CountUp to={5} duration={900} />
                </dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">servers involved</dt>
                <dd className="mt-1 font-mono text-2xl font-semibold text-white">
                  <CountUp to={0} />
                </dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">claims cited or flagged</dt>
                <dd className="mt-1 font-mono text-2xl font-semibold text-white">
                  <CountUp to={100} duration={1800} suffix="%" />
                </dd>
              </div>
            </dl>
          </div>

          <div className="animate-fade-up order-1 mx-auto aspect-square w-full max-w-[640px] lg:order-2" style={{ animationDelay: "0.2s" }}>
            <NetworkGlobe className="h-full w-full" />
          </div>
        </div>

      </section>

      {/* ================= MARQUEE ================= */}
      <section aria-label="Fields and connection types" className="relative space-y-4 border-y border-white/[0.06] bg-black/20 py-7 backdrop-blur-sm">
        <div className="text-2xl font-semibold tracking-tight text-white/80 sm:text-3xl">
          <MarqueeRow items={MARQUEE_A} dur="55s" />
        </div>
        <div className="font-mono text-sm text-cyan-200/70">
          <MarqueeRow items={MARQUEE_B} reverse dur="40s" />
        </div>
      </section>

      {/* ================= BENTO ================= */}
      <section className="relative mx-auto max-w-7xl px-6 pt-32">
        <Reveal className="max-w-3xl">
          <p className="eyebrow">Why it&apos;s different</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-6xl">
            Built on how admissions{" "}
            <span className="font-display italic font-normal metal-text">really</span> work.
          </h2>
        </Reveal>

        <div className="mt-14 grid auto-rows-[minmax(0,auto)] gap-4 md:grid-cols-6">
          {/* Connection-first */}
          <Reveal className="md:col-span-4 md:row-span-2">
            <div className="glass-card spotlight group relative h-full overflow-hidden rounded-3xl p-8">
              <p className="eyebrow">01 · Connection-first</p>
              <h3 className="mt-3 max-w-md text-3xl font-semibold tracking-tight text-white">
                Who you know, <span className="font-display italic font-normal text-cyan-200">verified.</span>
              </h3>
              <p className="mt-3 max-w-md text-zinc-400">
                Your advisor&apos;s real network is weighted ahead of raw prestige in
                every tier, because that is how committees actually read applications.
              </p>
              <div className="pointer-events-none mx-auto -mb-16 mt-2 w-full max-w-[460px] transition-transform duration-700 group-hover:scale-[1.04]">
                <ConstellationHero className="aspect-square w-full" />
              </div>
            </div>
          </Reveal>

          {/* Score */}
          <Reveal className="md:col-span-2" delay={100}>
            <div className="glass-card spotlight h-full rounded-3xl p-7 text-center">
              <p className="eyebrow">02 · Honest numbers</p>
              <div className="mt-5">
                <ScoreDemo />
              </div>
              <p className="mt-4 text-sm text-zinc-400">
                A relative-fit index with its uncertainty shown. Never a fake admit
                probability.
              </p>
            </div>
          </Reveal>

          {/* Private */}
          <Reveal className="md:col-span-2" delay={200}>
            <div className="glass-card spotlight relative h-full overflow-hidden rounded-3xl p-7">
              <p className="eyebrow">03 · Private</p>
              <div className="mt-4 flex items-baseline gap-3">
                <span className="font-mono text-7xl font-semibold leading-none text-white">0</span>
                <span className="text-sm text-zinc-400">servers. No accounts.</span>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-zinc-400">
                The engine is Python running in your browser. Your key and your CV
                never leave this device.
              </p>
              <IconShield className="absolute -bottom-6 -right-6 h-36 w-36 text-emerald-300/[0.07]" />
            </div>
          </Reveal>

          {/* Evidence terminal */}
          <Reveal className="md:col-span-3" delay={100}>
            <div className="glass-card spotlight flex h-full flex-col rounded-3xl p-7">
              <p className="eyebrow">04 · Evidence-first</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-white">
                Every claim has a source. Or a flag.
              </h3>
              <div className="mt-5 min-h-[190px] flex-1">
                <EvidenceTerminal />
              </div>
            </div>
          </Reveal>

          {/* Free */}
          <Reveal className="md:col-span-3" delay={200}>
            <div className="glass-card spotlight relative h-full overflow-hidden rounded-3xl p-7">
              <p className="eyebrow">05 · Free to start</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-white">
                Bring any key. Gemini&apos;s costs nothing.
              </h3>
              <div className="mt-6 flex flex-wrap gap-2">
                {["Claude", "OpenAI", "Gemini · free", "DeepSeek", "GLM", "MiniMax", "Any OpenAI-compatible"].map((p) => (
                  <span
                    key={p}
                    className={`rounded-full border px-3 py-1.5 text-sm ${
                      p.includes("free")
                        ? "border-emerald-300/40 bg-emerald-400/10 text-emerald-200"
                        : "border-white/10 bg-white/[0.03] text-zinc-300"
                    }`}
                  >
                    {p}
                  </span>
                ))}
              </div>
              <p className="mt-6 text-sm text-zinc-500">
                Providers with live web search give fully cited rankings.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ================= SCROLL PIPELINE ================= */}
      <section className="relative mt-24">
        <div className="beam mx-auto max-w-5xl" />
        <ScrollPipeline />
      </section>

      {/* ================= STEPS ================= */}
      <section className="relative mx-auto max-w-7xl px-6">
        <Reveal className="text-center">
          <p className="eyebrow">Three steps, about ten minutes</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
            From a blank page to a plan.
          </h2>
        </Reveal>
        <div className="relative mt-14 grid gap-4 md:grid-cols-3">
          <div aria-hidden="true" className="beam absolute left-[16%] right-[16%] top-[3.4rem] hidden md:block" />
          {[
            { Icon: IconKey, href: "/settings", title: "Bring a key", body: "Paste any LLM API key. Thirty seconds." },
            { Icon: IconUser, href: "/profile", title: "Tell your story", body: "Fill your profile, or drop in your CV to prefill it." },
            { Icon: IconCompass, href: "/dashboard", title: "Get your map", body: "A ranked, cited list of advisors with a move for each." },
          ].map((s, i) => (
            <Reveal key={s.title} delay={i * 120}>
              <Link href={s.href} className="glass-card spotlight group relative flex h-full flex-col items-center rounded-3xl p-8 text-center">
                <span className="metal-fill relative z-10 flex h-14 w-14 items-center justify-center rounded-2xl text-white shadow-[0_0_30px_rgba(99,102,241,0.45)] transition-transform duration-500 group-hover:-translate-y-1 group-hover:rotate-6">
                  <s.Icon className="h-6 w-6" />
                </span>
                <span className="font-display mt-5 text-sm italic text-zinc-500">step {i + 1}</span>
                <h3 className="mt-1 text-xl font-semibold text-white">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-400">{s.body}</p>
                <span className="mt-6 inline-flex items-center gap-1.5 text-sm text-indigo-300 transition-colors group-hover:text-white">
                  Go <IconArrow className="h-3.5 w-3.5 transition-transform duration-300 group-hover:translate-x-1" />
                </span>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ================= FINALE ================= */}
      <section className="relative mx-auto max-w-7xl px-6 pb-10 pt-40 text-center">
        <Reveal>
          <p aria-hidden="true" className="text-outline select-none text-[17vw] font-semibold leading-[0.85] tracking-[-0.05em] lg:text-[11rem]">
            stop guessing
          </p>
          <p className="-mt-[0.6em] text-5xl font-semibold tracking-[-0.03em] text-white sm:text-7xl lg:text-8xl">
            Start <span className="font-display italic font-normal metal-text">mapping.</span>
          </p>
        </Reveal>
        <Reveal delay={150}>
          <div className="mx-auto mt-14 max-w-2xl">
            <IconHeart className="mx-auto h-5 w-5 text-rose-300/90" />
            <p className="font-display mt-4 text-2xl italic leading-snug text-zinc-200 sm:text-[1.7rem]">
              Applying to a PhD is lonely work. You deserve a map that is honest
              about what it knows, and about what it doesn&apos;t.
            </p>
            <p className="mt-4 text-sm leading-relaxed text-zinc-500">
              申请博士是一段孤独的路。愿这张地图诚实地告诉你它知道什么、不知道什么，陪你找到那位真正适合你的导师。
            </p>
            <Link href="/settings" className="btn-primary group mt-10 rounded-2xl px-8 py-4 text-lg font-medium">
              Begin, it&apos;s free
              <IconArrow className="h-5 w-5 transition-transform duration-300 group-hover:translate-x-1" />
            </Link>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
