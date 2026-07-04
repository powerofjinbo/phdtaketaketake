import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def _default_skill_dir() -> Path:
    env = os.environ.get("PHDTAKE_SKILL_DIR")
    if env:
        return Path(env).expanduser()
    # Monorepo layout: repo_root/app/backend/app/config.py with the
    # phd_matcher engine at repo_root.
    repo_root = Path(__file__).resolve().parents[3]
    if (repo_root / "phd_matcher").is_dir():
        return repo_root
    return Path.home() / ".claude" / "skills" / "phdtaketaketake"


SKILL_DIR = _default_skill_dir()
DATA_DIR = SKILL_DIR / "data"
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./phdtake.db")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
RESEARCH_MAX_WEB_SEARCHES = int(os.environ.get("RESEARCH_MAX_WEB_SEARCHES", "40"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
