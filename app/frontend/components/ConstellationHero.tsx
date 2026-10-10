/**
 * ConstellationHero — the product's philosophy drawn as a picture.
 *
 * You sit at the centre. Advisors orbit around you. A line only lights up
 * when the connection is verified from a real source (solid, with signal
 * flowing along it); unverified links stay faint and dashed; a blocked source
 * is marked amber instead of being guessed. Connection-first, evidence-first.
 */

type Node = {
  x: number;
  y: number;
  r: number;
  state: "verified" | "missing" | "blocked";
  label?: string;
  delay: number;
};

const C = { x: 300, y: 300 };

const NODES: Node[] = [
  { x: 132, y: 168, r: 9, state: "verified", label: "co-author · 2024", delay: 0 },
  { x: 468, y: 150, r: 11, state: "verified", label: "same lab lineage", delay: 0.6 },
  { x: 520, y: 352, r: 8, state: "missing", delay: 1.2 },
  { x: 430, y: 486, r: 10, state: "verified", label: "shared grant", delay: 1.8 },
  { x: 214, y: 500, r: 8, state: "blocked", label: "source blocked", delay: 2.4 },
  { x: 86, y: 360, r: 7, state: "missing", delay: 3 },
  { x: 300, y: 92, r: 7, state: "missing", delay: 3.6 },
  { x: 560, y: 236, r: 5, state: "missing", delay: 1.5 },
  { x: 54, y: 250, r: 5, state: "missing", delay: 2.1 },
];

// Gentle curve from the centre to a node.
function edge(n: Node) {
  const mx = (C.x + n.x) / 2;
  const my = (C.y + n.y) / 2;
  const dx = n.x - C.x;
  const dy = n.y - C.y;
  const k = 0.12;
  return `M${C.x},${C.y} Q${mx - dy * k},${my + dx * k} ${n.x},${n.y}`;
}

const COLORS = {
  verified: "#67e8f9",
  missing: "#a1a1aa",
  blocked: "#fbbf77",
};

export default function ConstellationHero({ className = "" }: { className?: string }) {
  return (
    <div className={`relative ${className}`} aria-hidden="true">
      {/* soft halo behind the graph */}
      <div className="absolute inset-[12%] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.28),rgba(139,92,246,0.1)_45%,transparent_70%)] blur-2xl" />
      <svg viewBox="0 0 600 600" className="relative h-full w-full overflow-visible">
        <defs>
          <radialGradient id="ch-core" cx="50%" cy="50%" r="50%">
            <stop offset="0" stopColor="#fff7ed" />
            <stop offset="0.45" stopColor="#fbbf77" />
            <stop offset="1" stopColor="#fb7185" stopOpacity="0.9" />
          </radialGradient>
          <linearGradient id="ch-edge" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#a5b4fc" />
            <stop offset="1" stopColor="#67e8f9" />
          </linearGradient>
          <filter id="ch-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* orbit rings */}
        <g>
          <circle cx={C.x} cy={C.y} r="120" fill="none" stroke="rgba(165,180,252,0.2)" strokeDasharray="2 6" />
          <circle cx={C.x} cy={C.y} r="205" fill="none" stroke="rgba(165,180,252,0.14)" strokeDasharray="1 9" />
          <circle cx={C.x} cy={C.y} r="270" fill="none" stroke="rgba(165,180,252,0.05)" />
        </g>

        {/* edges */}
        {NODES.map((n, i) => {
          const d = edge(n);
          if (n.state === "verified") {
            return (
              <g key={`e${i}`}>
                <path d={d} fill="none" stroke="url(#ch-edge)" strokeOpacity="0.55" strokeWidth="1.6" />
                <path d={d} fill="none" stroke="#e0e7ff" strokeOpacity="0.5" strokeWidth="1.2" className="flow-dash" />
                <circle r="3" fill="#e0f2fe" filter="url(#ch-glow)" className="pulse-dot">
                  <animateMotion dur={`${2.6 + i * 0.35}s`} begin={`${n.delay}s`} repeatCount="indefinite" path={d} />
                </circle>
              </g>
            );
          }
          return (
            <path
              key={`e${i}`}
              d={d}
              fill="none"
              stroke={COLORS[n.state]}
              strokeOpacity={n.state === "blocked" ? 0.6 : 0.4}
              strokeWidth="1"
              strokeDasharray="3 6"
            />
          );
        })}

        {/* advisor nodes */}
        {NODES.map((n, i) => (
          <g
            key={`n${i}`}
            className="animate-drift"
            style={{ animationDelay: `${n.delay}s`, animationDuration: `${8 + (i % 4)}s` }}
          >
            {n.state === "verified" && (
              <circle cx={n.x} cy={n.y} r={n.r + 8} fill="#67e8f9" opacity="0.08" />
            )}
            <circle
              cx={n.x}
              cy={n.y}
              r={n.r}
              fill={n.state === "verified" ? "#0b1220" : "#0c0c14"}
              stroke={COLORS[n.state]}
              strokeOpacity={n.state === "missing" ? 0.75 : 0.95}
              strokeWidth="1.5"
              filter={n.state === "verified" ? "url(#ch-glow)" : undefined}
            />
            {n.state === "verified" && (
              <circle cx={n.x} cy={n.y} r={n.r * 0.4} fill="#a5f3fc" />
            )}
            {n.label && (
              <g transform={`translate(${n.x}, ${n.y + n.r + 18})`}>
                <rect
                  x={-n.label.length * 3.3 - 9}
                  y="-11"
                  width={n.label.length * 6.6 + 18}
                  height="22"
                  rx="11"
                  fill="rgba(10,10,20,0.75)"
                  stroke={n.state === "blocked" ? "rgba(251,191,119,0.45)" : "rgba(103,232,249,0.35)"}
                />
                <text
                  textAnchor="middle"
                  y="4"
                  fontSize="11"
                  fontFamily="var(--font-geist-mono), monospace"
                  fill={n.state === "blocked" ? "#fcd9a8" : "#cffafe"}
                >
                  {n.label}
                </text>
              </g>
            )}
          </g>
        ))}

        {/* you */}
        <g>
          <circle cx={C.x} cy={C.y} r="22" fill="#fbbf77" opacity="0.25" className="pulse-ring" style={{ transformOrigin: `${C.x}px ${C.y}px` }} />
          <circle cx={C.x} cy={C.y} r="40" fill="#fbbf77" opacity="0.07" />
          <circle cx={C.x} cy={C.y} r="20" fill="url(#ch-core)" filter="url(#ch-glow)" />
          <text x={C.x} y={C.y + 46} textAnchor="middle" fontSize="13" letterSpacing="2" fill="#fde7c7" fontFamily="var(--font-geist-sans), sans-serif">
            YOU
          </text>
        </g>
      </svg>
    </div>
  );
}
