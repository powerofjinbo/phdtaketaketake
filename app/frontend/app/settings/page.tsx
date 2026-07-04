"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type LlmSettings, type Provider } from "@/lib/api";

const inputCls =
  "w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none transition-colors placeholder:text-zinc-600 focus:border-indigo-400/60";
const labelCls = "mb-1.5 block text-sm text-zinc-300";

const PROVIDERS: {
  value: Provider;
  label: string;
  webSearch: boolean;
  defaultModel: string;
}[] = [
  {
    value: "anthropic",
    label: "Claude (Anthropic)",
    webSearch: true,
    defaultModel: "claude-sonnet-5",
  },
  { value: "openai", label: "OpenAI", webSearch: true, defaultModel: "gpt-5" },
  {
    value: "deepseek",
    label: "DeepSeek",
    webSearch: false,
    defaultModel: "deepseek-chat",
  },
  {
    value: "glm",
    label: "GLM (Zhipu 智谱)",
    webSearch: false,
    defaultModel: "glm-4.6",
  },
  {
    value: "gemini",
    label: "Gemini (Google)",
    webSearch: false,
    defaultModel: "gemini-2.5-pro",
  },
  {
    value: "minimax",
    label: "MiniMax",
    webSearch: false,
    defaultModel: "MiniMax-M2",
  },
  {
    value: "custom",
    label: "Custom (OpenAI-compatible)",
    webSearch: false,
    defaultModel: "your model id",
  },
];

const STEPS = [
  {
    n: 1,
    text: "Paste your LLM API key",
    href: null as string | null,
    label: "right below",
  },
  { n: 2, text: "Fill your profile (or import CV)", href: "/profile", label: "Profile" },
  { n: 3, text: "Run a match", href: "/dashboard", label: "Dashboard" },
];

export default function SettingsPage() {
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{
    kind: "ok" | "err";
    text: string;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<LlmSettings>("/settings")
      .then((s) => {
        if (cancelled) return;
        setProvider(s.provider);
        setModel(s.model ?? "");
        setBaseUrl(s.base_url ?? "");
        setHasKey(s.has_key);
      })
      .catch(() => {
        /* fresh settings */
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const meta = PROVIDERS.find((p) => p.value === provider) ?? PROVIDERS[0];

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const body: Record<string, string> = { provider };
      if (model.trim()) body.model = model.trim();
      if (provider === "custom" && baseUrl.trim())
        body.base_url = baseUrl.trim();
      if (apiKey.trim()) body.api_key = apiKey.trim();
      await api("/settings", { method: "PUT", body: JSON.stringify(body) });
      if (apiKey.trim()) setHasKey(true);
      setApiKey("");
      setMessage({ kind: "ok", text: "Settings saved." });
    } catch (err) {
      setMessage({
        kind: "err",
        text: err instanceof Error ? err.message : "Failed to save settings",
      });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16 text-zinc-500">
        Loading settings…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-white">Settings</h1>
      <p className="mt-2 text-sm text-zinc-400">
        Bring your own LLM API key. It powers the research agent behind your
        match runs.
      </p>

      {/* How it works */}
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {STEPS.map((s) => (
          <div
            key={s.n}
            className="rounded-xl border border-white/10 bg-white/[0.03] p-4"
          >
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

      <form
        onSubmit={save}
        className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6"
      >
        <h2 className="text-lg font-semibold text-white">LLM Provider</h2>

        <div className="mt-5 space-y-5">
          <div>
            <label className={labelCls}>Provider</label>
            <div className="flex items-center gap-3">
              <select
                className={inputCls}
                value={provider}
                onChange={(e) => setProvider(e.target.value as Provider)}
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
              <span
                className={`shrink-0 whitespace-nowrap rounded-full border px-2.5 py-1 text-xs ${
                  meta.webSearch
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border-amber-400/30 bg-amber-500/10 text-amber-300"
                }`}
              >
                {meta.webSearch ? "✅ live web search" : "⚠️ no web search"}
              </span>
            </div>
          </div>

          {!meta.webSearch && (
            <div className="rounded-xl border border-amber-400/30 bg-amber-500/[0.08] p-4 text-sm leading-relaxed text-amber-200">
              This provider has no web-search tool. The research agent will
              only suggest candidate names — every ranking will carry maximally
              wide confidence bands. For evidence-cited results use Claude or
              OpenAI.
            </div>
          )}

          <div>
            <label className={labelCls}>
              API key
              {hasKey && (
                <span className="ml-2 rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
                  key stored ✓
                </span>
              )}
            </label>
            <input
              type="password"
              className={inputCls}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={hasKey ? "Leave blank to keep existing key" : "sk-…"}
              autoComplete="off"
            />
          </div>

          <div>
            <label className={labelCls}>Model override (optional)</label>
            <input
              className={inputCls}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={`Default: ${meta.defaultModel}`}
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

          <div className="rounded-xl border border-indigo-400/30 bg-indigo-500/[0.07] p-4 text-sm leading-relaxed text-zinc-300">
            Anthropic and OpenAI providers run the research agent with live web
            search. Other providers have no web-search tool — runs will have
            much thinner evidence.
          </div>

          {message && (
            <p
              className={
                message.kind === "ok"
                  ? "text-sm text-emerald-400"
                  : "rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300"
              }
            >
              {message.text}
            </p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-gradient-to-r from-indigo-500 to-violet-600 px-6 py-2.5 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
        </div>
      </form>
    </div>
  );
}
