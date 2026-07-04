# PhDTake

Truth-based PhD advisor matching — a multi-user web app built on the
[phdtaketaketake](https://github.com/) connection-first scoring engine
(`phd_matcher`). Every ranking claim traces to a cited web source; missing
data widens the confidence band instead of being guessed.

## Architecture

```
frontend/   Next.js 14 + TypeScript + Tailwind (port 3000)
backend/    FastAPI + SQLAlchemy (SQLite dev / Postgres via DATABASE_URL, port 8000)
            ├─ auth: JWT email+password
            ├─ profile: StudentProfile validated by the engine's strict schema
            ├─ runs: background research→score pipeline per run
            ├─ research.py: Claude agent (web_search tool) discovers PIs and
            │   collects evidence-cited signals under the data-integrity contract
            └─ engine.py: bridge to phd_matcher (deterministic CAPEG scoring,
                risk/difficulty adjustment, strategy buckets)
```

The scoring engine is imported from the skill checkout at
`PHDTAKE_SKILL_DIR` (default `~/.claude/skills/phdtaketaketake`).

## Run locally

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
.venv/bin/uvicorn app.main:app --port 8000 --reload

# frontend
cd frontend
npm install
npm run dev            # http://localhost:3000
```

## Flow

1. Register → fill your profile (field, GPA, research direction, current
   advisors, papers, experiences).
2. Start a match run (target tier or school list, top-k, optional
   strict-evidence mode).
3. The backend spawns a Claude research agent that web-searches candidate
   PIs, verifies connection edges to your advisors, and records structured
   evidence. The deterministic engine then ranks by
   `difficulty_adjusted_strength` and assigns apply buckets.
4. Results render as evidence-cited candidate cards with confidence bands.

> This is a 4.0-scale relative application-strength index, not an admission
> probability. Missing or blocked sources widen the confidence band instead
> of being guessed.

## LLM providers (bring your own key)

Each user configures their provider under **Settings**:

| provider | web search | default model |
|---|---|---|
| Claude (Anthropic) | ✅ server-side web_search tool | `claude-sonnet-5` |
| OpenAI | ✅ Responses API web_search tool | `gpt-5` |
| Custom OpenAI-compatible (`base_url`) | ❌ none | user-specified |

Keys are stored encrypted at rest (Fernet keyed off `JWT_SECRET`). Without
web search (custom providers), the research agent is instructed to emit
suggestion-only candidates with no unverified claims — rankings then carry
maximally wide confidence bands, per the data-integrity contract. A
server-level `ANTHROPIC_API_KEY` in `.env` acts as fallback for users with
no key of their own.

## CV import

On the profile page, upload a text-based PDF CV. The backend extracts the
text (pypdf) and the user's LLM parses it into the strict `StudentProfile`
schema — extraction only, no embellishment. Nothing is saved until the user
reviews and clicks Save.

## Hosting on GitHub

GitHub Pages serves **static files only**, so the split is:

- **Frontend → GitHub Pages** (free): `.github/workflows/deploy-pages.yml`
  builds the static export (`output: "export"`) and deploys on every push to
  `main`. Set the repo *variable* `PHDTAKE_API_URL` to your backend URL, and
  enable Pages → Source: GitHub Actions in repo settings.
- **Backend → any free-tier host** (Render / Fly.io / Railway):
  `uvicorn app.main:app` with the `phd_matcher` engine vendored alongside.
  Set `CORS_ORIGINS=https://<username>.github.io`.

## Deploying

- Set `DATABASE_URL` to Postgres, `JWT_SECRET` to a strong secret,
  `CORS_ORIGINS` to your frontend origin, and vendor the engine (copy the
  skill's `phd_matcher/` + `data/` next to the backend, point
  `PHDTAKE_SKILL_DIR` at it).
- Each match run costs real Anthropic API tokens (a web-search research
  turn); the API caps users at 2 concurrent runs — add real quotas/billing
  before opening it publicly.
