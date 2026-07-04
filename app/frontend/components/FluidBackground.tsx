"use client";

/**
 * FluidBackground — a fixed, full-viewport WebGL canvas rendered with Three.js.
 *
 * This is a PURELY DECORATIVE layer. It renders a single full-screen plane with
 * a custom GLSL fragment shader: domain-warped flow noise + metaball-like energy
 * currents + a fresnel/refraction rim, tinted with indigo/violet/cyan energy over
 * a near-black field. The goal is an *engineered / computational* liquid — data
 * that has become fluid — never a natural ocean.
 *
 * All heavy lifting happens on the GPU in one draw call, so it stays cheap.
 *
 * Robustness + performance safeguards (all required, all implemented here):
 *   - Renders nothing until mounted on the client (static-export / SSG safe).
 *   - prefers-reduced-motion → render a single static frame, no RAF loop.
 *   - Pauses the RAF loop when document.hidden or the canvas is offscreen.
 *   - Caps devicePixelRatio (≤1.5, ≤1.0 on mobile) and throttles to ~40fps.
 *   - Downscales resolution on small viewports.
 *   - try/catch around WebGL init; any failure → CSS gradient fallback, never a
 *     blank/broken canvas or a crash.
 *   - Full cleanup on unmount: cancelAnimationFrame, dispose, remove listeners,
 *     lose the WebGL context.
 */

import { useEffect, useRef, useState } from "react";

// A calm CSS liquid-gradient used whenever WebGL is unavailable, disabled, or on
// very small / reduced-motion contexts where we skip the shader entirely.
const CSS_FALLBACK: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: -1,
  pointerEvents: "none",
  background:
    "radial-gradient(120% 90% at 18% 8%, rgba(79,70,229,0.20) 0%, rgba(9,9,15,0) 42%)," +
    "radial-gradient(110% 100% at 85% 20%, rgba(139,92,246,0.16) 0%, rgba(9,9,15,0) 46%)," +
    "radial-gradient(120% 120% at 60% 100%, rgba(34,211,238,0.12) 0%, rgba(9,9,15,0) 50%)," +
    "#07070c",
};

const VERTEX_SHADER = /* glsl */ `
  precision highp float;
  attribute vec2 position;
  varying vec2 vUv;
  void main() {
    vUv = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
  }
`;

// Raymarch-free "liquid metal / data current" field. We build a height field from
// stacked, domain-warped fbm noise, derive a cheap normal from it, then light it
// with a hard chrome highlight + a fresnel rim + energy currents. Everything is
// pushed toward indigo / violet / cyan over near-black, and the motion is slow and
// engineered (flowing along a fixed direction, not sloshing like water).
const FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform vec2  uResolution;
  uniform float uTime;
  uniform float uQuality;   // 1.0 = full, <1.0 = fewer octaves (mobile)

  // ---- hash / value noise -------------------------------------------------
  vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(dot(hash2(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
          dot(hash2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
      mix(dot(hash2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
          dot(hash2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x),
      u.y);
  }

  // fractal brownian motion — flows along a fixed "data current" direction.
  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    vec2 flow = vec2(0.14, 0.05);        // constant engineered drift
    mat2 rot = mat2(0.80, 0.60, -0.60, 0.80);
    int oct = uQuality > 0.5 ? 6 : 4;
    for (int i = 0; i < 6; i++) {
      if (i >= oct) break;
      v += a * noise(p + flow * uTime * float(i + 1) * 0.35);
      p = rot * p * 1.92 + 4.0;
      a *= 0.5;
    }
    return v;
  }

  // domain-warped height field — the "liquid" surface.
  float surface(vec2 p, out vec2 warp) {
    float t = uTime * 0.06;
    vec2 q = vec2(fbm(p + vec2(0.0, t)), fbm(p + vec2(5.2, 1.3 - t)));
    vec2 r = vec2(fbm(p + 3.0 * q + vec2(1.7, 9.2) + 0.15 * t),
                  fbm(p + 3.0 * q + vec2(8.3, 2.8) - 0.12 * t));
    warp = r;
    return fbm(p + 2.4 * r);
  }

  // metaball-like energy currents — bright cores that drift and pulse, giving the
  // "intelligence flowing through a network" read.
  float energyCurrents(vec2 uv) {
    float e = 0.0;
    for (int i = 0; i < 3; i++) {
      float fi = float(i);
      vec2 c = vec2(
        0.5 + 0.42 * sin(uTime * 0.10 + fi * 2.2),
        0.5 + 0.34 * cos(uTime * 0.08 + fi * 1.7)
      );
      float d = length((uv - c) * vec2(uResolution.x / uResolution.y, 1.0));
      e += 0.045 / (d * d + 0.02);
    }
    return e;
  }

  void main() {
    vec2 uv = vUv;
    vec2 p = (gl_FragCoord.xy - 0.5 * uResolution.xy) / uResolution.y;
    p *= 2.6;

    // height field + cheap analytic normal from finite differences.
    vec2 warp;
    float h = surface(p, warp);
    float eps = 0.012;
    vec2 w2;
    float hx = surface(p + vec2(eps, 0.0), w2);
    float hy = surface(p + vec2(0.0, eps), w2);
    vec3 n = normalize(vec3(h - hx, h - hy, eps * 3.2));

    // lighting: a single crisp "engineered" key light for the chrome highlight.
    vec3 lightDir = normalize(vec3(0.55, 0.62, 0.75));
    vec3 viewDir = vec3(0.0, 0.0, 1.0);
    vec3 halfDir = normalize(lightDir + viewDir);

    float diff = clamp(dot(n, lightDir), 0.0, 1.0);
    float spec = pow(clamp(dot(n, halfDir), 0.0, 1.0), 42.0);  // liquid-metal glint
    float fres = pow(1.0 - clamp(dot(n, viewDir), 0.0, 1.0), 3.0); // rim

    // palette — near-black base, indigo → violet body, cyan energy.
    vec3 base    = vec3(0.024, 0.024, 0.045);
    vec3 indigo  = vec3(0.31, 0.27, 0.90);
    vec3 violet  = vec3(0.55, 0.33, 0.95);
    vec3 cyan    = vec3(0.16, 0.85, 0.95);
    vec3 chrome  = vec3(0.78, 0.80, 0.92);

    float body = smoothstep(-0.35, 0.65, h);
    vec3 col = mix(base, indigo, body * 0.72);
    col = mix(col, violet, smoothstep(0.1, 0.9, warp.x * 0.5 + 0.5) * 0.45);

    // flowing "data current" veins along the warp gradient — thin bright threads.
    float veins = smoothstep(0.75, 0.99, fbm(p * 1.6 + warp * 2.0 + uTime * 0.05));
    col += cyan * veins * 0.38;

    // chrome highlight + fresnel rim = the engineered / refractive look. Kept
    // controlled so highlights don't blow out under overlaid UI text.
    col += chrome * spec * 0.85;
    col += mix(indigo, cyan, 0.5) * fres * 0.32;
    col *= 0.5 + 0.7 * diff;

    // metaball energy cores (kept subtle so the UI stays legible on top).
    float energy = energyCurrents(uv);
    col += mix(violet, cyan, 0.5) * energy * 0.26;

    // vignette so page content reads clearly toward the edges + center.
    float vig = smoothstep(1.35, 0.2, length(uv - 0.5));
    col *= 0.34 + 0.6 * vig;

    // subtle filmic-ish tonemap; hold it dark and premium (the UI does the rest).
    col = col / (col + 1.05);
    col = pow(col, vec3(0.95));

    gl_FragColor = vec4(col, 1.0);
  }
`;

export default function FluidBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Start in "not-yet-mounted" state so SSG renders only the CSS fallback and we
  // never touch window / WebGL during prerender.
  const [useFallback, setUseFallback] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Small / reduced-motion detection.
    const reduceMotion = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const isMobile = window.matchMedia?.("(max-width: 640px)").matches;

    // Cleanup handles populated during init; called on every early-return path.
    let renderer: import("three").WebGLRenderer | null = null;
    let mesh: import("three").Mesh | null = null;
    let geometry: import("three").BufferGeometry | null = null;
    let material: import("three").RawShaderMaterial | null = null;
    let rafId = 0;
    let running = true;
    let visible = true;
    let observer: IntersectionObserver | null = null;
    let disposed = false;
    const cleanupFns: Array<() => void> = [];

    // Everything below can throw (unsupported WebGL, driver quirks, OOM). If it
    // does, we simply leave the CSS fallback in place.
    (async () => {
      try {
        const THREE = await import("three");
        if (disposed) return;

        renderer = new THREE.WebGLRenderer({
          canvas,
          antialias: false,
          alpha: false,
          powerPreference: "low-power",
          failIfMajorPerformanceCaveat: false,
        });

        // Cap DPR hard: ≤1.0 on mobile, ≤1.5 elsewhere. Downscale further on
        // small viewports so the fragment shader stays cheap.
        const baseDpr = Math.min(window.devicePixelRatio || 1, isMobile ? 1.0 : 1.5);
        const renderScale = isMobile ? 0.6 : 0.85;

        const scene = new THREE.Scene();
        const camera = new THREE.Camera();

        geometry = new THREE.BufferGeometry();
        // One oversized "fullscreen triangle" that fully covers the clip-space
        // quad (cheaper than two triangles, no seam).
        const verts = new Float32Array([-1, -1, 3, -1, -1, 3]);
        geometry.setAttribute("position", new THREE.BufferAttribute(verts, 2));
        geometry.setDrawRange(0, 3);
        // Give it an explicit, finite bounding sphere so three never tries to
        // auto-compute one from our 2-component position attribute (which would
        // read z as NaN and log a warning).
        geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), 2);

        // RawShaderMaterial (NOT ShaderMaterial): three's ShaderMaterial injects
        // its own `attribute vec3 position` + built-in prelude, which collides
        // with our fullscreen-triangle `attribute vec2 position`. Raw gives us a
        // bare shader with exactly the declarations we wrote.
        material = new THREE.RawShaderMaterial({
          vertexShader: VERTEX_SHADER,
          fragmentShader: FRAGMENT_SHADER,
          depthTest: false,
          depthWrite: false,
          uniforms: {
            uResolution: { value: new THREE.Vector2(1, 1) },
            uTime: { value: 0 },
            uQuality: { value: isMobile ? 0.0 : 1.0 },
          },
        });
        // We handle the fullscreen triangle ourselves; no frustum culling.
        mesh = new THREE.Mesh(geometry, material);
        mesh.frustumCulled = false;
        scene.add(mesh);

        const resize = () => {
          if (!renderer || !material) return;
          const w = window.innerWidth;
          const h = window.innerHeight;
          renderer.setPixelRatio(baseDpr * renderScale);
          renderer.setSize(w, h, false);
          const px = renderer.getDrawingBufferSize(new THREE.Vector2());
          (material.uniforms.uResolution.value as import("three").Vector2).set(
            px.x,
            px.y
          );
        };
        resize();

        const renderFrame = (timeSeconds: number) => {
          if (!renderer || !material) return;
          (material.uniforms.uTime.value as number) = timeSeconds;
          renderer.render(scene, camera);
        };

        // We only made it here → real WebGL is up; hide the CSS fallback.
        setUseFallback(false);

        // Static path: reduced motion → one frame, no loop, no listeners beyond
        // resize (kept so an orientation change still looks right).
        if (reduceMotion) {
          renderFrame(6.0); // a pleasant, settled frame
          window.addEventListener("resize", () => {
            resize();
            renderFrame(6.0);
          });
          return;
        }

        // Animated path — throttled to ~40fps, paused when hidden/offscreen.
        const FRAME_MS = 1000 / 40;
        let last = 0;
        const start = performance.now();

        const loop = (now: number) => {
          rafId = requestAnimationFrame(loop);
          if (!running || !visible) return;
          if (now - last < FRAME_MS) return;
          last = now;
          renderFrame((now - start) / 1000);
        };
        rafId = requestAnimationFrame(loop);

        const onVisibility = () => {
          running = !document.hidden;
        };
        document.addEventListener("visibilitychange", onVisibility);

        // Pause when the canvas is scrolled fully offscreen.
        observer = new IntersectionObserver(
          (entries) => {
            visible = entries[0]?.isIntersecting ?? true;
          },
          { threshold: 0 }
        );
        observer.observe(canvas);

        window.addEventListener("resize", resize);

        // Register teardown for these animated-path listeners.
        cleanupFns.push(() => {
          document.removeEventListener("visibilitychange", onVisibility);
          window.removeEventListener("resize", resize);
        });
      } catch {
        // WebGL unavailable or shader failed to compile → keep CSS fallback.
        setUseFallback(true);
      }
    })();

    return () => {
      disposed = true;
      running = false;
      if (rafId) cancelAnimationFrame(rafId);
      cleanupFns.forEach((fn) => fn());
      observer?.disconnect();
      geometry?.dispose();
      material?.dispose();
      if (renderer) {
        // Force the driver to release the context immediately.
        renderer.forceContextLoss?.();
        renderer.dispose();
      }
      renderer = null;
      mesh = null;
      geometry = null;
      material = null;
    };
  }, []);

  return (
    <>
      {/* Canvas: fixed, behind everything, ignores pointer events. */}
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="fluid-canvas"
        style={{
          position: "fixed",
          inset: 0,
          width: "100%",
          height: "100%",
          zIndex: -1,
          pointerEvents: "none",
          display: "block",
        }}
      />
      {/* CSS fallback sits under the canvas; visible when WebGL is off/failed or
          during SSG before hydration. */}
      {useFallback && <div aria-hidden="true" style={CSS_FALLBACK} />}
    </>
  );
}
