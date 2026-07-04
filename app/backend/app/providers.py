"""LLM provider abstraction — Anthropic, OpenAI, or any OpenAI-compatible API.

Each user brings their own key (stored encrypted). Anthropic and OpenAI run
the research agent WITH live web search (server-side tools); custom
OpenAI-compatible endpoints have no web-search tool, so runs on them carry an
honest coverage warning instead of pretending to have searched.
"""

from dataclasses import dataclass

from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, RESEARCH_MAX_WEB_SEARCHES
from .crypto import decrypt
from .models import UserSettings

# Provider presets. Everything except "anthropic" speaks the OpenAI wire
# format; non-OpenAI vendors are reached via their OpenAI-compatible base
# URLs. Only anthropic/openai expose a server-side web-search tool — the
# rest run the research agent in honest no-web-search mode.
PROVIDER_PRESETS: dict[str, dict] = {
    "anthropic": {"model": ANTHROPIC_MODEL, "base_url": None},
    "openai": {"model": "gpt-5", "base_url": None},
    "deepseek": {"model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1"},
    "glm": {"model": "glm-4.6", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    "minimax": {"model": "MiniMax-M2", "base_url": "https://api.minimaxi.com/v1"},
    "gemini": {
        "model": "gemini-2.5-pro",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "custom": {"model": "", "base_url": None},
}
PROVIDERS = tuple(PROVIDER_PRESETS)
DEFAULT_MODELS = {k: v["model"] for k, v in PROVIDER_PRESETS.items()}
WEB_SEARCH_PROVIDERS = ("anthropic", "openai")


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None = None

    @property
    def has_web_search(self) -> bool:
        return self.provider in WEB_SEARCH_PROVIDERS


def resolve_llm_config(settings: UserSettings | None) -> LLMConfig | None:
    """User settings first; server-level Anthropic key as fallback."""
    if settings and settings.api_key_encrypted:
        key = decrypt(settings.api_key_encrypted)
        if key:
            provider = settings.provider if settings.provider in PROVIDERS else "anthropic"
            preset = PROVIDER_PRESETS[provider]
            return LLMConfig(
                provider=provider,
                api_key=key,
                model=settings.model or preset["model"],
                base_url=settings.base_url or preset["base_url"],
            )
    if ANTHROPIC_API_KEY:
        return LLMConfig(provider="anthropic", api_key=ANTHROPIC_API_KEY, model=ANTHROPIC_MODEL)
    return None


# ---------------------------------------------------------------------------
# Research-agent completion (long agentic turn, web search where supported)
# ---------------------------------------------------------------------------

def run_agent_turn(cfg: LLMConfig, system: str, user_msg: str, on_progress=None) -> str:
    if cfg.provider == "anthropic":
        return _anthropic_turn(cfg, system, user_msg, on_progress)
    if cfg.provider == "openai":
        return _openai_turn(cfg, system, user_msg, web_search=True)
    return _openai_turn(cfg, system, user_msg, web_search=False)


def _anthropic_turn(cfg: LLMConfig, system: str, user_msg: str, on_progress) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.api_key)
    messages = [{"role": "user", "content": user_msg}]
    searches, text = 0, ""
    while True:
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=16000,
            system=system,
            messages=messages,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": RESEARCH_MAX_WEB_SEARCHES,
                }
            ],
        )
        for block in resp.content:
            if block.type == "server_tool_use":
                searches += 1
            elif block.type == "text":
                text += block.text
        if on_progress:
            on_progress(f"research agent: {searches} web searches so far")
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        return text


def _openai_turn(cfg: LLMConfig, system: str, user_msg: str, *, web_search: bool) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None)
    if web_search:
        resp = client.responses.create(
            model=cfg.model,
            instructions=system,
            input=user_msg,
            tools=[{"type": "web_search"}],
        )
        return resp.output_text
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
    )
    return resp.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Short one-shot completion (CV parsing — no web search needed)
# ---------------------------------------------------------------------------

def run_completion(cfg: LLMConfig, system: str, user_msg: str) -> str:
    if cfg.provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=cfg.api_key)
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")
    return _openai_turn(cfg, system, user_msg, web_search=False)
