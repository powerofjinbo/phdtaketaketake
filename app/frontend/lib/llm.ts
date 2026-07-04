// Browser-direct LLM clients. Every provider is called straight from the
// user's browser with their own key — verified CORS-compatible for all of
// them. Keys never leave this device except to the provider itself.

export type Provider =
  | "anthropic"
  | "openai"
  | "gemini"
  | "deepseek"
  | "glm"
  | "minimax"
  | "custom";

export interface ProviderInfo {
  label: string;
  defaultModel: string;
  baseUrl: string | null; // OpenAI-compatible base (null = native API)
  webSearch: boolean;
  keyUrl: string; // where users create a key
  keyNote: string;
}

export const PROVIDERS: Record<Provider, ProviderInfo> = {
  anthropic: {
    label: "Claude (Anthropic)",
    defaultModel: "claude-sonnet-5",
    baseUrl: null,
    webSearch: true,
    keyUrl: "https://console.anthropic.com/settings/keys",
    keyNote: "Paid API key. Live web search — evidence-cited rankings.",
  },
  openai: {
    label: "OpenAI",
    defaultModel: "gpt-5",
    baseUrl: null,
    webSearch: true,
    keyUrl: "https://platform.openai.com/api-keys",
    keyNote: "Paid API key. Live web search — evidence-cited rankings.",
  },
  gemini: {
    label: "Gemini (Google) — free tier",
    defaultModel: "gemini-2.5-flash",
    baseUrl: null,
    webSearch: true, // native google_search grounding
    keyUrl: "https://aistudio.google.com/apikey",
    keyNote:
      "FREE API key from Google AI Studio (generous free tier). Web search via Google grounding.",
  },
  deepseek: {
    label: "DeepSeek",
    defaultModel: "deepseek-chat",
    baseUrl: "https://api.deepseek.com/v1",
    webSearch: false,
    keyUrl: "https://platform.deepseek.com/api_keys",
    keyNote: "Very cheap API key. No web search — suggestion-only candidates.",
  },
  glm: {
    label: "GLM (Zhipu 智谱)",
    defaultModel: "glm-4.6",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4",
    webSearch: false,
    keyUrl: "https://open.bigmodel.cn/usercenter/apikeys",
    keyNote: "Cheap API key. No web search — suggestion-only candidates.",
  },
  minimax: {
    label: "MiniMax",
    defaultModel: "MiniMax-M2",
    baseUrl: "https://api.minimaxi.com/v1",
    webSearch: false,
    keyUrl: "https://platform.minimaxi.com/user-center/basic-information/interface-key",
    keyNote: "API key. No web search — suggestion-only candidates.",
  },
  custom: {
    label: "Custom (OpenAI-compatible)",
    defaultModel: "",
    baseUrl: null,
    webSearch: false,
    keyUrl: "",
    keyNote:
      "Any OpenAI-compatible endpoint (must allow browser CORS). No web search.",
  },
};

export interface LlmSettings {
  provider: Provider;
  apiKey: string;
  model?: string;
  baseUrl?: string; // custom only
}

export function resolvedModel(s: LlmSettings): string {
  return s.model?.trim() || PROVIDERS[s.provider].defaultModel;
}

function resolvedBase(s: LlmSettings): string {
  if (s.provider === "custom") return (s.baseUrl || "").replace(/\/$/, "");
  return (PROVIDERS[s.provider].baseUrl || "").replace(/\/$/, "");
}

export function hasWebSearch(p: Provider): boolean {
  return PROVIDERS[p].webSearch;
}

async function readError(resp: Response): Promise<string> {
  let detail = `${resp.status} ${resp.statusText}`;
  try {
    const body = await resp.json();
    detail =
      body?.error?.message || body?.message || JSON.stringify(body).slice(0, 300);
  } catch {
    /* keep status text */
  }
  return detail;
}

// ---------------------------------------------------------------------------
// Agent turn — long completion, with provider-native web search where available
// ---------------------------------------------------------------------------

export async function agentTurn(
  s: LlmSettings,
  system: string,
  userMsg: string,
  onProgress?: (note: string) => void
): Promise<string> {
  if (s.provider === "anthropic")
    return anthropicTurn(s, system, userMsg, onProgress);
  if (s.provider === "openai") return openaiResponsesTurn(s, system, userMsg);
  if (s.provider === "gemini") return geminiTurn(s, system, userMsg, true);
  return openaiChatTurn(s, system, userMsg);
}

// Short one-shot completion (CV parsing) — no web search needed.
export async function completion(
  s: LlmSettings,
  system: string,
  userMsg: string
): Promise<string> {
  if (s.provider === "anthropic") {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: anthropicHeaders(s),
      body: JSON.stringify({
        model: resolvedModel(s),
        max_tokens: 8000,
        system,
        messages: [{ role: "user", content: userMsg }],
      }),
    });
    if (!resp.ok) throw new Error(await readError(resp));
    const data = await resp.json();
    return (data.content || [])
      .filter((b: { type: string }) => b.type === "text")
      .map((b: { text: string }) => b.text)
      .join("");
  }
  if (s.provider === "gemini") return geminiTurn(s, system, userMsg, false);
  if (s.provider === "openai") {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${s.apiKey}`,
      },
      body: JSON.stringify({
        model: resolvedModel(s),
        messages: [
          { role: "system", content: system },
          { role: "user", content: userMsg },
        ],
      }),
    });
    if (!resp.ok) throw new Error(await readError(resp));
    const data = await resp.json();
    return data.choices?.[0]?.message?.content || "";
  }
  return openaiChatTurn(s, system, userMsg);
}

function anthropicHeaders(s: LlmSettings): Record<string, string> {
  return {
    "content-type": "application/json",
    "x-api-key": s.apiKey,
    "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  };
}

async function anthropicTurn(
  s: LlmSettings,
  system: string,
  userMsg: string,
  onProgress?: (note: string) => void
): Promise<string> {
  const messages: unknown[] = [{ role: "user", content: userMsg }];
  let text = "";
  let searches = 0;
  for (let i = 0; i < 8; i++) {
    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: anthropicHeaders(s),
      body: JSON.stringify({
        model: resolvedModel(s),
        max_tokens: 16000,
        system,
        messages,
        tools: [
          { type: "web_search_20250305", name: "web_search", max_uses: 40 },
        ],
      }),
    });
    if (!resp.ok) throw new Error(await readError(resp));
    const data = await resp.json();
    for (const block of data.content || []) {
      if (block.type === "server_tool_use") searches++;
      else if (block.type === "text") text += block.text;
    }
    onProgress?.(`research agent: ${searches} web searches so far`);
    if (data.stop_reason === "pause_turn") {
      messages.push({ role: "assistant", content: data.content });
      continue;
    }
    return text;
  }
  return text;
}

async function openaiResponsesTurn(
  s: LlmSettings,
  system: string,
  userMsg: string
): Promise<string> {
  const resp = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${s.apiKey}`,
    },
    body: JSON.stringify({
      model: resolvedModel(s),
      instructions: system,
      input: userMsg,
      tools: [{ type: "web_search" }],
    }),
  });
  if (!resp.ok) throw new Error(await readError(resp));
  const data = await resp.json();
  let text = "";
  for (const item of data.output || []) {
    if (item.type === "message") {
      for (const c of item.content || []) {
        if (c.type === "output_text") text += c.text;
      }
    }
  }
  return text || data.output_text || "";
}

async function geminiTurn(
  s: LlmSettings,
  system: string,
  userMsg: string,
  withSearch: boolean
): Promise<string> {
  const model = resolvedModel(s);
  const resp = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-goog-api-key": s.apiKey,
      },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: system }] },
        contents: [{ role: "user", parts: [{ text: userMsg }] }],
        ...(withSearch ? { tools: [{ google_search: {} }] } : {}),
        generationConfig: { maxOutputTokens: 16000 },
      }),
    }
  );
  if (!resp.ok) throw new Error(await readError(resp));
  const data = await resp.json();
  const parts = data.candidates?.[0]?.content?.parts || [];
  return parts
    .map((p: { text?: string }) => p.text || "")
    .join("");
}

async function openaiChatTurn(
  s: LlmSettings,
  system: string,
  userMsg: string
): Promise<string> {
  const base = resolvedBase(s);
  if (!base) throw new Error("This provider needs a base URL");
  const resp = await fetch(`${base}/chat/completions`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${s.apiKey}`,
    },
    body: JSON.stringify({
      model: resolvedModel(s),
      messages: [
        { role: "system", content: system },
        { role: "user", content: userMsg },
      ],
    }),
  });
  if (!resp.ok) throw new Error(await readError(resp));
  const data = await resp.json();
  return data.choices?.[0]?.message?.content || "";
}

// ---------------------------------------------------------------------------
// Key test — a real (tiny) call so users know their key works BEFORE a run
// ---------------------------------------------------------------------------

export async function testKey(s: LlmSettings): Promise<{ ok: boolean; message: string }> {
  try {
    if (!s.apiKey.trim()) return { ok: false, message: "Enter an API key first" };
    if (s.provider === "anthropic") {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: anthropicHeaders(s),
        body: JSON.stringify({
          model: resolvedModel(s),
          max_tokens: 16,
          messages: [{ role: "user", content: "Say OK" }],
        }),
      });
      if (!resp.ok) return { ok: false, message: await readError(resp) };
      return { ok: true, message: `Key works (${resolvedModel(s)})` };
    }
    if (s.provider === "gemini") {
      const out = await geminiTurn(s, "Reply with exactly: OK", "ping", false);
      return { ok: true, message: `Key works (${resolvedModel(s)}) — “${out.trim().slice(0, 20)}”` };
    }
    if (s.provider === "openai") {
      const resp = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${s.apiKey}`,
        },
        body: JSON.stringify({
          model: resolvedModel(s),
          max_completion_tokens: 16,
          messages: [{ role: "user", content: "Say OK" }],
        }),
      });
      if (!resp.ok) return { ok: false, message: await readError(resp) };
      return { ok: true, message: `Key works (${resolvedModel(s)})` };
    }
    const out = await openaiChatTurn(s, "Reply with exactly: OK", "ping");
    return { ok: true, message: `Key works (${resolvedModel(s)}) — “${out.trim().slice(0, 20)}”` };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.includes("Failed to fetch"))
      return {
        ok: false,
        message:
          "Could not reach the provider from your browser (network or CORS block). Check your connection, or try Claude / OpenAI / Gemini which are verified browser-compatible.",
      };
    return { ok: false, message: msg };
  }
}
