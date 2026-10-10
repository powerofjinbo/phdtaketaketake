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
import PageHeader from "@/components/PageHeader";
import { IconArrow, IconCheck, IconEye, IconKey, IconShield } from "@/components/Icons";

const inputCls = "field";
const labelCls = "field-label";

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
  const [showKey, setShowKey] = useState(false);
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
    <div className="mx-auto max-w-3xl px-6 py-12">
      <PageHeader
        eyebrow="Step 1 · API key"
        title={
          <>
            Bring your own{" "}
            <span className="font-display italic font-normal text-[1.1em] metal-text">key</span>
          </>
        }
      >
        It powers the research agent behind your match runs. Don&apos;t have one?
        Gemini&apos;s is free.
      </PageHeader>

      {/* How it works */}
      <ol className="animate-fade-up delay-100 mt-8 grid gap-3 sm:grid-cols-3">
        {STEPS.map((s) => {
          const current = s.n === 1;
          const body = (
            <>
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-xs ${
                  current ? "metal-fill text-white shadow-[0_0_16px_rgba(99,102,241,0.5)]" : "bg-white/[0.06] text-zinc-400"
                }`}
              >
                {s.n}
              </span>
              <span className="min-w-0">
                <span className={`block text-sm ${current ? "text-white" : "text-zinc-300"}`}>{s.text}</span>
                <span className={`block text-xs ${current ? "text-indigo-200/80" : "text-zinc-500"}`}>
                  {current ? "You are here" : `${s.label} →`}
                </span>
              </span>
            </>
          );
          return (
            <li key={s.n}>
              {s.href ? (
                <Link href={s.href} className="glass-card flex h-full items-center gap-3 rounded-xl p-4">
                  {body}
                </Link>
              ) : (
                <div className="glass aurora-border flex h-full items-center gap-3 rounded-xl p-4">{body}</div>
              )}
            </li>
          );
        })}
      </ol>

      <form onSubmit={onSave} className="animate-fade-up delay-200 glass mt-6 rounded-2xl p-6 sm:p-7">
        <div className="flex items-center gap-3">
          <span className="metal-fill rounded-xl p-2 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)]">
            <IconKey className="h-5 w-5" />
          </span>
          <h2 className="text-lg font-semibold text-white">LLM provider</h2>
        </div>

        <div className="mt-5 space-y-5">
          <div>
            <span className={labelCls}>Provider</span>
            <div role="radiogroup" className="grid gap-2 sm:grid-cols-2">
              {PROVIDER_ORDER.map((p) => {
                const on = provider === p;
                const pi = PROVIDERS[p];
                return (
                  <button
                    key={p}
                    type="button"
                    role="radio"
                    aria-checked={on}
                    onClick={() => {
                      setProvider(p);
                      setTestResult(null);
                    }}
                    className={`flex items-center justify-between gap-3 rounded-xl border px-3.5 py-2.5 text-left transition-all duration-300 ${
                      on
                        ? "border-indigo-300/60 bg-indigo-500/15 shadow-[0_0_0_3px_rgba(99,102,241,0.15)]"
                        : "border-white/[0.08] bg-black/20 hover:border-white/20"
                    }`}
                  >
                    <span className={`text-sm ${on ? "font-medium text-white" : "text-zinc-300"}`}>{pi.label}</span>
                    <span
                      title={pi.webSearch ? "Live web search" : "No web search"}
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                        pi.webSearch ? "bg-emerald-400/12 text-emerald-300" : "bg-white/[0.05] text-zinc-500"
                      }`}
                    >
                      {pi.webSearch ? "web" : "offline"}
                    </span>
                  </button>
                );
              })}
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
            <div className="relative">
            <input
              type={showKey ? "text" : "password"}
              className={`${inputCls} pr-11 font-mono`}
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setTestResult(null);
              }}
              placeholder="sk-…"
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="button"
              onClick={() => setShowKey((v) => !v)}
              aria-label={showKey ? "Hide key" : "Show key"}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-zinc-500 transition-colors hover:text-zinc-200"
            >
              <IconEye off={showKey} />
            </button>
            </div>
            <p className="mt-1.5 text-xs text-zinc-500">
              {info.keyUrl && (
                <>
                  <a
                    href={info.keyUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-300 hover:underline"
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
              className="btn-primary rounded-xl px-6 py-2.5 font-medium"
            >
              Save settings
            </button>
            <button
              type="button"
              onClick={onTest}
              disabled={testing}
              className="btn-ghost rounded-xl px-5 py-2.5 text-sm disabled:opacity-50"
            >
              {testing ? "Testing…" : "Test key"}
            </button>
            {testing && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-400/30 border-t-indigo-300" />
            )}
            {saved && (
              <span className="animate-fade-up flex items-center gap-1.5 text-sm text-emerald-300">
                <IconCheck /> Saved
              </span>
            )}
            {saved && (
              <Link href="/profile" className="animate-fade-up ml-auto inline-flex items-center gap-1 text-sm text-indigo-300 hover:text-white">
                Next: your profile <IconArrow className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>

          {saveError && (
            <p className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {saveError}
            </p>
          )}

          {testResult && (
            <p
              className={`animate-fade-up rounded-xl border px-3 py-2 text-sm ${
                testResult.ok
                  ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                  : "border-rose-400/30 bg-rose-500/10 text-rose-200"
              }`}
            >
              {testResult.ok ? "✓ " : "✗ "}
              {testResult.message}
            </p>
          )}

          <p className="flex items-start gap-2 text-xs leading-relaxed text-zinc-500">
            <IconShield className="mt-px h-4 w-4 shrink-0 text-emerald-300/70" />
            <span>Your key is stored only in this browser (localStorage) and sent
            only to the provider you chose — there is no PhDTake server at all.</span>
          </p>
        </div>
      </form>

      {/* Subscription explainer */}
      <div className="glass mt-6 overflow-hidden rounded-2xl">
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
