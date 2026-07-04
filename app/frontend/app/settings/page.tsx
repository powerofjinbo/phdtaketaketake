"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  PROVIDERS,
  testKey,
  type LlmSettings,
  type Provider,
} from "@/lib/llm";
import { loadSettings, saveSettings } from "@/lib/store";

const inputCls =
  "w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none backdrop-blur transition-colors placeholder:text-zinc-600 focus:border-indigo-400/60";
const labelCls = "mb-1.5 block text-sm text-zinc-300";

// Registry order already puts Gemini (free key) right after Claude/OpenAI.
const PROVIDER_ORDER = Object.keys(PROVIDERS) as Provider[];

const STEPS = [
  { n: 1, text: "Paste your LLM API key", href: null as string | null, label: "right below" },
  { n: 2, text: "Fill your profile (or import CV)", href: "/profile", label: "Profile" },
  { n: 3, text: "Run a match", href: "/dashboard", label: "Dashboard" },
];

export default function SettingsPage() {
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [subOpen, setSubOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      const s = loadSettings();
      if (s) {
        setProvider(s.provider);
        setApiKey(s.apiKey ?? "");
        setModel(s.model ?? "");
        setBaseUrl(s.baseUrl ?? "");
      }
      setLoaded(true);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  const info = PROVIDERS[provider];

  function currentSettings(): LlmSettings {
    return {
      provider,
      apiKey: apiKey.trim(),
      model: model.trim() || undefined,
      baseUrl: provider === "custom" ? baseUrl.trim() || undefined : undefined,
    };
  }

  function onSave(e: React.FormEvent) {
    e.preventDefault();
    const s = currentSettings();
    // Custom endpoints have no default model — without one, every later call
    // would send model:"" and fail at run time. Require it, like base_url.
    if (s.provider === "custom" && !s.model) {
      setSaveError(
        "Custom providers need a model name (there is no default) — enter one above."
      );
      return;
    }
    setSaveError(null);
    saveSettings(s);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  async function onTest() {
    setTesting(true);
    setTestResult(null);
    try {
      setTestResult(await testKey(currentSettings()));
    } finally {
      setTesting(false);
    }
  }

  if (!loaded) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16 text-zinc-500">
        Loading settings…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-white">Settings</h1>
      <p className="mt-2 text-sm text-zinc-300/90">
        Bring your own LLM API key. It powers the research agent behind your
        match runs.
      </p>

      {/* How it works */}
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="glass-card rounded-xl p-4">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500/30 to-violet-600/30 font-mono text-xs text-indigo-300">
              {s.n}
            </span>
            <p className="mt-2 text-sm text-zinc-300">{s.text}</p>
            {s.href ? (
              <Link
                href={s.href}
                className="mt-1 inline-block text-xs text-indigo-400 hover:underline"
              >
                {s.label} →
              </Link>
            ) : (
              <span className="mt-1 inline-block text-xs text-zinc-600">
                {s.label} ↓
              </span>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={onSave} className="glass mt-6 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white">LLM Provider</h2>

        <div className="mt-5 space-y-5">
          <div>
            <label className={labelCls}>Provider</label>
            <div className="flex items-center gap-3">
              <select
                className={inputCls}
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value as Provider);
                  setTestResult(null);
                }}
              >
                {PROVIDER_ORDER.map((p) => (
                  <option key={p} value={p}>
                    {PROVIDERS[p].label}
                  </option>
                ))}
              </select>
              <span
                className={`shrink-0 whitespace-nowrap rounded-full border px-2.5 py-1 text-xs ${
                  info.webSearch
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-amber-400/30 bg-amber-500/10 text-amber-300"
                }`}
              >
                {info.webSearch ? "✅ live web search" : "⚠️ no web search"}
              </span>
            </div>
          </div>

          {!info.webSearch && (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/[0.08] p-4 text-sm leading-relaxed text-amber-200">
              This provider has no web-search tool. The research agent will
              only suggest candidate names — every ranking will carry maximally
              wide confidence bands. For evidence-cited results use Claude or
              OpenAI.
            </div>
          )}

          <div>
            <label className={labelCls}>API key</label>
            <input
              type="password"
              className={inputCls}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestResult(null);
              }}
              placeholder="sk-…"
              autoComplete="off"
            />
            <p className="mt-1.5 text-xs text-zinc-500">
              {info.keyUrl && (
                <>
                  <a
                    href={info.keyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:underline"
                  >
                    Get a key →
                  </a>{" "}
                </>
              )}
              {info.keyNote}
            </p>
          </div>

          <div>
            <label className={labelCls}>Model override (optional)</label>
            <input
              className={inputCls}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={
                info.defaultModel
                  ? `Default: ${info.defaultModel}`
                  : "e.g. llama-3.3-70b"
              }
            />
          </div>

          {provider === "custom" && (
            <div>
              <label className={labelCls}>Base URL</label>
              <input
                type="url"
                required
                className={inputCls}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://your-endpoint.example.com/v1"
              />
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              className="btn-primary rounded-lg px-6 py-2.5 font-medium"
            >
              Save settings
            </button>
            <button
              type="button"
              onClick={onTest}
              disabled={testing}
              className="btn-ghost rounded-lg px-5 py-2.5 text-sm disabled:opacity-50"
            >
              {testing ? "Testing…" : "Test key"}
            </button>
            {saved && <span className="text-sm text-emerald-400">Saved ✓</span>}
          </div>

          {saveError && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {saveError}
            </p>
          )}

          {testResult && (
            <p
              className={`rounded-lg border px-3 py-2 text-sm ${
                testResult.ok
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-red-500/30 bg-red-500/10 text-red-300"
              }`}
            >
              {testResult.ok ? "✓ " : "✗ "}
              {testResult.message}
            </p>
          )}

          <p className="text-xs leading-relaxed text-zinc-500">
            Your key is stored only in this browser (localStorage) and sent
            only to the provider you chose — there is no PhDTake server at all.
          </p>
        </div>
      </form>

      {/* Subscription explainer */}
      <div className="glass mt-6 rounded-2xl">
        <button
          type="button"
          onClick={() => setSubOpen((o) => !o)}
          className="flex w-full items-center justify-between px-6 py-4 text-left text-sm font-medium text-zinc-200 hover:text-white"
        >
          <span>
            Why can&apos;t I log in with my ChatGPT / Claude subscription?
          </span>
          <span
            className={`text-zinc-500 transition-transform ${subOpen ? "rotate-180" : ""}`}
          >
            ▾
          </span>
        </button>
        {subOpen && (
          <div className="border-t border-white/10 px-6 py-4 text-sm leading-relaxed text-zinc-400">
            <p>
              Honest answer: LLM vendors do not let third-party apps use
              consumer subscriptions — there is no public OAuth for ChatGPT
              Plus or Claude Pro. API keys are the supported path for apps like
              this one.
            </p>
            <p className="mt-2">
              If you don&apos;t want to pay for another key: Gemini&apos;s API
              key is free (Google AI Studio), and DeepSeek / GLM keys are very
              cheap.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
