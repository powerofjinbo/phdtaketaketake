"use client";

import { useEffect, useRef, useState } from "react";

/** Runs `fn` once when the element first scrolls into view. */
function useInView<T extends HTMLElement>(threshold = 0.3) {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, seen };
}

function useReducedMotion() {
  const [r, setR] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setR(window.matchMedia("(prefers-reduced-motion: reduce)").matches), 0);
    return () => clearTimeout(t);
  }, []);
  return r;
}

/** Counts from 0 to `to` once visible. */
export function CountUp({
  to,
  decimals = 0,
  duration = 1600,
  suffix = "",
  className = "",
}: {
  to: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
  className?: string;
}) {
  const { ref, seen } = useInView<HTMLSpanElement>();
  const reduced = useReducedMotion();
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!seen) return;
    if (reduced) {
      const t = setTimeout(() => setV(to), 0);
      return () => clearTimeout(t);
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      setV(to * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, to, duration, reduced]);
  return (
    <span ref={ref} className={className}>
      {v.toFixed(decimals)}
      {suffix}
    </span>
  );
}

/** A sample score ring that fills and settles once visible. */
export function ScoreDemo() {
  const { ref, seen } = useInView<HTMLDivElement>();
  const r = 52;
  const c = 2 * Math.PI * r;
  const value = 3.42;
  const band = 0.3;
  return (
    <div ref={ref} className="relative mx-auto h-44 w-44">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <defs>
          <linearGradient id="demo-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#818cf8" />
            <stop offset="0.6" stopColor="#c084fc" />
            <stop offset="1" stopColor="#67e8f9" />
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="9" />
        {/* confidence band */}
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke="rgba(165,180,252,0.25)"
          strokeWidth="9"
          strokeDasharray={`${(c * band * 2) / 4} ${c}`}
          strokeDashoffset={-((value - band) / 4) * c}
          style={{ opacity: seen ? 1 : 0, transition: "opacity 0.8s 1.2s" }}
        />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke="url(#demo-ring)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={seen ? c * (1 - value / 4) : c}
          style={{ transition: "stroke-dashoffset 1.8s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <CountUp to={value} decimals={2} className="font-mono text-4xl font-semibold text-white" />
        <span className="mt-0.5 font-mono text-xs text-indigo-200/70">±{band.toFixed(2)} band</span>
      </div>
    </div>
  );
}

const LOG = [
  { s: "ok", t: "co-author with your advisor · OpenAlex 2024" },
  { s: "ok", t: "active NSF grant · nsf.gov" },
  { s: "miss", t: "recruiting status · not found → band widened" },
  { s: "ok", t: "placed 3 students in faculty roles · lab site" },
  { s: "block", t: "lab page · 403 blocked → flagged, not guessed" },
  { s: "ok", t: "shared center membership · dept page" },
];

/** A looping terminal that types out evidence checks. */
export function EvidenceTerminal() {
  const { ref, seen } = useInView<HTMLDivElement>();
  const reduced = useReducedMotion();
  const [lines, setLines] = useState<{ s: string; t: string }[]>([]);
  const [typing, setTyping] = useState("");
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!seen) return;
    if (reduced) {
      const t = setTimeout(() => setLines(LOG), 0);
      return () => clearTimeout(t);
    }
    const item = LOG[idx % LOG.length];
    if (typing.length < item.t.length) {
      const t = setTimeout(() => setTyping(item.t.slice(0, typing.length + 1)), 22);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      setLines((l) => [...l, item].slice(-5));
      setTyping("");
      setIdx((i) => i + 1);
    }, 650);
    return () => clearTimeout(t);
  }, [seen, typing, idx, reduced]);

  const mark = (s: string) =>
    s === "ok" ? (
      <span className="text-emerald-300">✓</span>
    ) : s === "miss" ? (
      <span className="text-zinc-500">○</span>
    ) : (
      <span className="text-amber-300">△</span>
    );
  const color = (s: string) => (s === "ok" ? "text-zinc-300" : s === "miss" ? "text-zinc-500" : "text-amber-200/90");
  const current = LOG[idx % LOG.length];

  return (
    <div ref={ref} className="h-full rounded-xl border border-white/[0.07] bg-black/50 p-4 font-mono text-[11.5px] leading-relaxed">
      <div className="mb-3 flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-rose-400/70" />
        <span className="h-2 w-2 rounded-full bg-amber-300/70" />
        <span className="h-2 w-2 rounded-full bg-emerald-400/70" />
        <span className="ml-2 text-[10px] uppercase tracking-wider text-zinc-600">evidence agent</span>
      </div>
      <ul className="space-y-1.5">
        {lines.map((l, i) => (
          <li key={`${i}-${l.t}`} className={`flex gap-2 ${color(l.s)}`}>
            {mark(l.s)}
            <span>{l.t}</span>
          </li>
        ))}
        {!reduced && (
          <li className={`flex gap-2 ${color(current.s)}`}>
            <span className="text-cyan-300">›</span>
            <span>
              {typing}
              <span className="caret text-cyan-300" />
            </span>
          </li>
        )}
      </ul>
    </div>
  );
}

const LAYERS = [
  { k: "Match", f: "w_C·C + w_A·A + w_P·P + w_E·E + w_G·G", v: 3.62, note: "Connection carries the most weight in every tier." },
  { k: "Strength", f: "match + opportunity", v: 3.71, note: "Funding, lab capacity and recruiting nudge it." },
  { k: "Risk", f: "strength − band / 2", v: 3.56, note: "Every unverified signal costs you here, honestly." },
  { k: "Difficulty", f: "risk − program penalty", v: 3.11, note: "A harder program lowers the bar you can count on." },
  { k: "Strategy", f: "bucket(difficulty, evidence)", v: 3.11, note: "Priority, target or reach. Never changes the score." },
];

/** Scroll-driven walk through the five scoring layers. */
export function ScrollPipeline() {
  const ref = useRef<HTMLDivElement>(null);
  const [p, setP] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const r = el.getBoundingClientRect();
        const total = r.height - window.innerHeight;
        setP(total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : 0);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  const active = Math.min(LAYERS.length - 1, Math.floor(p * LAYERS.length));
  const layer = LAYERS[active];
  const isStrategy = active === LAYERS.length - 1;

  return (
    <div ref={ref} className="relative" style={{ height: `${LAYERS.length * 70 + 40}vh` }}>
      <div className="sticky top-0 flex min-h-screen items-center py-20 lg:py-24">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-8 px-6 lg:grid-cols-[1fr_1.1fr] lg:gap-12">
          <div>
            <p className="eyebrow">Transparent scoring</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Five layers.
              <br />
              <span className="font-display italic font-normal metal-text">No black box.</span>
            </h2>
            <div className="mt-6 flex gap-1.5 lg:hidden" aria-hidden="true">
              {LAYERS.map((l, i) => (
                <span
                  key={l.k}
                  className={`h-1 flex-1 rounded-full transition-colors duration-500 ${
                    i <= active ? "bg-gradient-to-r from-indigo-400 to-cyan-300" : "bg-white/10"
                  }`}
                />
              ))}
            </div>
            <ol className="mt-10 hidden space-y-2 lg:block">
              {LAYERS.map((l, i) => {
                const on = i === active;
                const done = i < active;
                return (
                  <li
                    key={l.k}
                    className={`flex items-center gap-4 rounded-xl px-4 py-3 transition-all duration-500 ${
                      on ? "glass translate-x-2" : ""
                    }`}
                  >
                    <span
                      className={`font-mono text-sm transition-colors duration-500 ${
                        on ? "text-cyan-300" : done ? "text-indigo-300/60" : "text-zinc-700"
                      }`}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className={`text-lg transition-colors duration-500 ${on ? "font-semibold text-white" : done ? "text-zinc-400" : "text-zinc-600"}`}>
                      {l.k}
                    </span>
                    {on && <span className="ml-auto hidden font-mono text-xs text-zinc-500 sm:block">{l.f}</span>}
                  </li>
                );
              })}
            </ol>
          </div>

          <div className="glass-strong aurora-border relative overflow-hidden rounded-3xl p-6 sm:p-10">
            <div aria-hidden="true" className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-indigo-500/25 blur-3xl" />
            <p className="relative font-mono text-xs uppercase tracking-[0.2em] text-zinc-500">
              Layer {active + 1} · {layer.k}
            </p>
            <div className="relative mt-6 flex items-end gap-4">
              <span
                key={layer.k}
                className="animate-fade-up font-mono text-6xl font-semibold leading-none tracking-tight text-white sm:text-8xl"
              >
                {isStrategy ? "" : layer.v.toFixed(2)}
                {isStrategy && <span className="ember-text font-sans">Priority</span>}
              </span>
              {!isStrategy && <span className="mb-2 font-mono text-lg text-zinc-500">/ 4.0</span>}
            </div>
            {/* 0–4 track with a moving marker */}
            <div className="relative mt-8 h-2 rounded-full bg-white/[0.06] sm:mt-10">
              <div
                className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-400 transition-all duration-700 ease-out"
                style={{ width: `${(layer.v / 4) * 100}%` }}
              />
              {active >= 2 && (
                <div
                  className="absolute inset-y-0 rounded-full bg-indigo-300/25 ring-1 ring-inset ring-indigo-200/30 transition-all duration-700"
                  style={{ left: `${((3.71 - 0.3) / 4) * 100}%`, width: `${(0.6 / 4) * 100}%` }}
                />
              )}
              <div
                className="absolute top-1/2 h-5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_14px_rgba(255,255,255,0.7)] transition-all duration-700 ease-out"
                style={{ left: `${(layer.v / 4) * 100}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between font-mono text-[10px] text-zinc-600">
              {[0, 1, 2, 3, 4].map((n) => (
                <span key={n}>{n}</span>
              ))}
            </div>
            <p key={`n-${layer.k}`} className="animate-fade-up relative mt-6 text-base leading-relaxed text-zinc-300 sm:mt-8 sm:text-lg">
              {layer.note}
            </p>
            <p className="relative mt-3 font-mono text-xs text-zinc-600">Illustrative example, not a real candidate.</p>
            <div className="relative mt-8 h-1 overflow-hidden rounded-full bg-white/[0.05]">
              <div className="h-full bg-gradient-to-r from-indigo-400 to-cyan-300" style={{ width: `${p * 100}%` }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
