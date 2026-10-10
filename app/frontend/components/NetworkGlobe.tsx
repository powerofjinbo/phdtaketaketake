"use client";

/**
 * NetworkGlobe — the academic world as a slowly turning sphere of researchers.
 *
 * One ember node is you. Arcs leap from you only to advisors whose connection
 * is verified; pulses of signal travel along them. Everyone else is a faint
 * point in the mesh. Drag to spin it; it also leans toward the cursor.
 *
 * Canvas 2D (no second WebGL context next to the fluid background), additive
 * blending for glow, pre-rendered glow sprites, DPR capped, paused when hidden
 * or offscreen, and a single static frame under prefers-reduced-motion.
 */

import { useEffect, useRef } from "react";

type V3 = [number, number, number];

const N = 150;
// Verified links go to nodes near "you" (by distance rank), so arcs stay
// readable instead of spanning the whole globe.
const LINK_SPECS = [
  { rank: 4, label: "co-author · 2024" },
  { rank: 9, label: "lab lineage" },
  { rank: 15, label: "shared grant" },
  { rank: 22, label: "same center" },
  { rank: 30, label: "committee" },
  { rank: 6, label: "" },
  { rank: 12, label: "" },
];
const YOU = 0;

function fibonacciSphere(n: number): V3[] {
  const pts: V3[] = [];
  const phi = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const t = phi * i;
    pts.push([Math.cos(t) * r, y, Math.sin(t) * r]);
  }
  return pts;
}

function sprite(color: string, size: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const g = c.getContext("2d")!;
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grd.addColorStop(0, color);
  grd.addColorStop(0.25, color.replace(/[\d.]+\)$/, "0.45)"));
  grd.addColorStop(1, color.replace(/[\d.]+\)$/, "0)"));
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  return c;
}

export default function NetworkGlobe({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const labelsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const labelHost = labelsRef.current;
    if (!canvas || !labelHost) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const base = fibonacciSphere(N);
    // Move "you" to a front-facing spot so the story reads at a glance.
    base[YOU] = [-0.12, 0.08, 0.99];

    const byDist = base
      .map((p, j) => ({ j, d: (p[0] - base[YOU][0]) ** 2 + (p[1] - base[YOU][1]) ** 2 + (p[2] - base[YOU][2]) ** 2 }))
      .filter((x) => x.j !== YOU)
      .sort((a, b) => a.d - b.d);
    const LINKS = LINK_SPECS.map((l) => ({ to: byDist[l.rank].j, label: l.label }));

    // Mesh: each node to its 3 nearest neighbours.
    const mesh: [number, number][] = [];
    for (let i = 0; i < N; i++) {
      const d = base
        .map((p, j) => ({ j, d: (p[0] - base[i][0]) ** 2 + (p[1] - base[i][1]) ** 2 + (p[2] - base[i][2]) ** 2 }))
        .filter((x) => x.j !== i)
        .sort((a, b) => a.d - b.d)
        .slice(0, 3);
      for (const { j } of d) if (i < j) mesh.push([i, j]);
    }

    const glowCyan = sprite("rgba(103,232,249,1)", 64);
    const glowIndigo = sprite("rgba(165,180,252,1)", 64);
    const glowEmber = sprite("rgba(251,191,119,1)", 128);

    const labelEls = LINKS.map((l) => {
      const el = document.createElement("div");
      el.className =
        "pointer-events-none absolute left-0 top-0 whitespace-nowrap rounded-full border border-cyan-300/30 bg-[#070712]/80 px-2.5 py-1 font-mono text-[10px] text-cyan-100 backdrop-blur transition-opacity duration-300";
      el.textContent = l.label;
      el.style.opacity = "0";
      if (l.label) labelHost.appendChild(el);
      return el;
    });
    const youEl = document.createElement("div");
    youEl.className =
      "pointer-events-none absolute left-0 top-0 rounded-full border border-amber-200/40 bg-amber-300/10 px-3 py-1 text-[11px] font-semibold tracking-[0.2em] text-amber-100 backdrop-blur";
    youEl.textContent = "YOU";
    labelHost.appendChild(youEl);

    let w = 0;
    let h = 0;
    let dpr = 1;
    const resize = () => {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = r.width;
      h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    // Interaction state.
    // User rotation (drag, with inertia) on top of a slow auto-sway that keeps
    // "you" mostly facing the viewer.
    let userY = 0;
    let rotY = 0;
    let rotX = -0.12;
    let velY = 0;
    let tiltX = 0;
    let tiltY = 0;
    let targetTiltX = 0;
    let targetTiltY = 0;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    const onDown = (e: PointerEvent) => {
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      targetTiltY = ((e.clientX - r.left) / r.width - 0.5) * 0.35;
      targetTiltX = ((e.clientY - r.top) / r.height - 0.5) * 0.25;
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;
      userY += dx * 0.006;
      rotX = Math.max(-1.1, Math.min(1.1, rotX + dy * 0.004));
      velY = dx * 0.0006;
    };
    const onUp = () => {
      dragging = false;
    };
    canvas.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerup", onUp);

    const project = (p: V3, R: number, cx: number, cy: number) => {
      const ay = rotY + tiltY;
      const ax = rotX + tiltX;
      const cY = Math.cos(ay), sY = Math.sin(ay);
      const cX = Math.cos(ax), sX = Math.sin(ax);
      const x1 = p[0] * cY + p[2] * sY;
      const z1 = -p[0] * sY + p[2] * cY;
      const y1 = p[1] * cX - z1 * sX;
      const z2 = p[1] * sX + z1 * cX;
      const persp = 2.6 / (2.6 - z2);
      return { x: cx + x1 * R * persp, y: cy + y1 * R * persp, z: z2, s: persp };
    };

    // Point on the arc between two unit vectors, lifted off the surface.
    const arcPoint = (a: V3, b: V3, t: number): V3 => {
      const x = a[0] + (b[0] - a[0]) * t;
      const y = a[1] + (b[1] - a[1]) * t;
      const z = a[2] + (b[2] - a[2]) * t;
      const len = Math.hypot(x, y, z) || 1;
      const lift = 1 + Math.sin(Math.PI * t) * 0.16;
      return [(x / len) * lift, (y / len) * lift, (z / len) * lift];
    };

    let raf = 0;
    let visible = true;
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible && !raf && !reduced) raf = requestAnimationFrame(frame);
    });
    io.observe(canvas);

    const start = performance.now();
    function frame(now: number) {
      raf = 0;
      const t = (now - start) / 1000;
      if (!dragging) {
        userY += velY;
        velY *= 0.96;
      }
      rotY = userY + Math.sin(t * 0.12) * 0.75;
      tiltX += (targetTiltX - tiltX) * 0.05;
      tiltY += (targetTiltY - tiltY) * 0.05;

      const cx = w / 2;
      const cy = h / 2;
      const R = Math.min(w, h) * 0.34;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx!.clearRect(0, 0, w, h);

      // Atmosphere + rim.
      const atm = ctx!.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 1.45);
      atm.addColorStop(0, "rgba(99,102,241,0.0)");
      atm.addColorStop(0.55, "rgba(99,102,241,0.16)");
      atm.addColorStop(0.75, "rgba(34,211,238,0.06)");
      atm.addColorStop(1, "rgba(99,102,241,0)");
      ctx!.fillStyle = atm;
      ctx!.beginPath();
      ctx!.arc(cx, cy, R * 1.45, 0, Math.PI * 2);
      ctx!.fill();
      const body = ctx!.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.1, cx, cy, R * 1.05);
      body.addColorStop(0, "rgba(40,40,80,0.35)");
      body.addColorStop(1, "rgba(6,6,14,0.55)");
      ctx!.fillStyle = body;
      ctx!.beginPath();
      ctx!.arc(cx, cy, R * 1.04, 0, Math.PI * 2);
      ctx!.fill();
      ctx!.strokeStyle = "rgba(165,180,252,0.18)";
      ctx!.lineWidth = 1;
      ctx!.stroke();
      // Rim light from the upper left.
      const rim = ctx!.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
      rim.addColorStop(0, "rgba(165,243,252,0.75)");
      rim.addColorStop(0.35, "rgba(165,180,252,0.25)");
      rim.addColorStop(0.7, "rgba(165,180,252,0)");
      ctx!.strokeStyle = rim;
      ctx!.lineWidth = 2;
      ctx!.beginPath();
      ctx!.arc(cx, cy, R * 1.04, Math.PI * 0.9, Math.PI * 1.75);
      ctx!.stroke();

      const P = base.map((p) => project(p, R, cx, cy));

      // Mesh lines (depth-faded).
      ctx!.globalCompositeOperation = "lighter";
      ctx!.lineWidth = 0.7;
      for (const [i, j] of mesh) {
        const a = P[i], b = P[j];
        const depth = (a.z + b.z) / 2;
        const alpha = 0.04 + Math.max(0, depth + 0.2) * 0.2;
        ctx!.strokeStyle = `rgba(165,180,252,${alpha})`;
        ctx!.beginPath();
        ctx!.moveTo(a.x, a.y);
        ctx!.lineTo(b.x, b.y);
        ctx!.stroke();
      }

      // Nodes.
      for (let i = 0; i < N; i++) {
        if (i === YOU) continue;
        const p = P[i];
        const front = (p.z + 1) / 2;
        const linked = LINKS.some((l) => l.to === i);
        const size = (linked ? 26 : 11) * p.s * (0.55 + front * 0.6);
        ctx!.globalAlpha = linked ? 1 : 0.15 + front * 0.75;
        ctx!.drawImage(linked ? glowCyan : glowIndigo, p.x - size / 2, p.y - size / 2, size, size);
      }
      ctx!.globalAlpha = 1;

      // Verified arcs from you, with travelling pulses.
      const you = base[YOU];
      LINKS.forEach((l, k) => {
        const target = base[l.to];
        const steps = 40;
        let prev = project(arcPoint(you, target, 0), R, cx, cy);
        for (let s = 1; s <= steps; s++) {
          const q = project(arcPoint(you, target, s / steps), R, cx, cy);
          const a = 0.18 + Math.max(0, (prev.z + q.z) / 2 + 0.3) * 0.5;
          ctx!.strokeStyle = `rgba(103,232,249,${a})`;
          ctx!.lineWidth = 1.3;
          ctx!.beginPath();
          ctx!.moveTo(prev.x, prev.y);
          ctx!.lineTo(q.x, q.y);
          ctx!.stroke();
          prev = q;
        }
        const ph = ((t * 0.45 + k * 0.37) % 1 + 1) % 1;
        const pp = project(arcPoint(you, target, ph), R, cx, cy);
        const ps = 26 * pp.s;
        ctx!.drawImage(glowCyan, pp.x - ps / 2, pp.y - ps / 2, ps, ps);

        const tp = P[l.to];
        const el = labelEls[k];
        if (l.label) {
          el.style.transform = `translate(${tp.x + 12}px, ${tp.y - 10}px)`;
          el.style.opacity = tp.z > 0.05 ? "1" : "0";
        }
      });

      // You.
      const yp = P[YOU];
      const pulse = 1 + Math.sin(t * 2.4) * 0.12;
      const ys = 90 * yp.s * pulse;
      ctx!.drawImage(glowEmber, yp.x - ys / 2, yp.y - ys / 2, ys, ys);
      ctx!.globalCompositeOperation = "source-over";
      ctx!.fillStyle = "#fff7ed";
      ctx!.beginPath();
      ctx!.arc(yp.x, yp.y, 4.2 * yp.s, 0, Math.PI * 2);
      ctx!.fill();
      // expanding ring
      const ringT = (t * 0.6) % 1;
      ctx!.strokeStyle = `rgba(251,191,119,${0.6 * (1 - ringT)})`;
      ctx!.lineWidth = 1.2;
      ctx!.beginPath();
      ctx!.arc(yp.x, yp.y, 8 + ringT * 40, 0, Math.PI * 2);
      ctx!.stroke();
      youEl.style.transform = `translate(${yp.x - 22}px, ${yp.y + 16}px)`;
      youEl.style.opacity = yp.z > -0.1 ? "1" : "0.25";

      if (!reduced && visible && !document.hidden) raf = requestAnimationFrame(frame);
    }

    const onVis = () => {
      if (!document.hidden && visible && !raf && !reduced) raf = requestAnimationFrame(frame);
    };
    document.addEventListener("visibilitychange", onVis);
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      canvas.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      document.removeEventListener("visibilitychange", onVis);
      labelHost.replaceChildren();
    };
  }, []);

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={ref}
        className="absolute inset-0 h-full w-full cursor-grab touch-pan-y active:cursor-grabbing"
        aria-label="An animated sphere of researchers. Your verified connections light up."
        role="img"
      />
      <div ref={labelsRef} aria-hidden="true" className="absolute inset-0 overflow-hidden" />
    </div>
  );
}
