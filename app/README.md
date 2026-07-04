# PhDTake — web app

Truth-based PhD advisor matching, built on the
[phdtaketaketake](../README.md) connection-first scoring engine
(`phd_matcher`). Every ranking claim traces to a cited web source; missing
data widens the confidence band instead of being guessed.

**Live app: https://powerofjinbo.github.io/phdtaketaketake/**

## Architecture — fully client-side

There is **no server**. The static site (GitHub Pages) is the entire app:

```
frontend/                Next.js 16 static export (output: "export")
├─ lib/llm.ts            browser-direct LLM clients — Claude / OpenAI /
│                        Gemini (live web search) + DeepSeek / GLM /
│                        MiniMax / custom (honest no-search mode).
│                        All verified browser-CORS-compatible.
├─ lib/research.ts       the research-agent pipeline (data-integrity
│                        contract in the system prompt)
├─ public/engine-worker.js  module Web Worker running the EXACT
│                        phd_matcher Python engine via Pyodide
├─ scripts/fetch-pyodide.mjs   self-hosts the Pyodide runtime + wheels
│                        (no third-party CDN at runtime)
├─ scripts/bundle-engine.mjs   bundles phd_matcher + data/ from the repo
│                        root into public/engine/bundle.json
└─ lib/store.ts          profile / settings / runs in localStorage
```

- **No signup.** Nothing to log into; data lives in the browser.
- **Bring your own key.** The user's API key is stored in localStorage and
  sent only to their chosen provider. Gemini keys are free
  (aistudio.google.com/apikey); a one-click "Test key" button proves the
  key works before any run.
- **Why no "subscription login"?** LLM vendors do not let third-party apps
  use consumer ChatGPT/Claude subscriptions (there is no public OAuth for
  that). API keys are the supported path; the UI explains this honestly.

## Develop

```bash
cd frontend
npm install
npm run dev     # prebuild self-hosts pyodide + bundles the engine
npm run build   # static export → out/
```

Deployed by `.github/workflows/deploy-pages.yml` on every push to `main`.

## Optional API twin

`backend/` contains a FastAPI implementation of the same pipeline (JWT
auth, encrypted BYOK, server-side runs). It is **not** used by the website
— kept for teams who prefer a hosted deployment (see `render.yaml` at the
repo root).

> This is a 4.0-scale relative application-strength index, not an admission
> probability. Missing or blocked sources widen the confidence band instead
> of being guessed.
