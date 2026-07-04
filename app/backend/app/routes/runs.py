from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Profile, Run, User, UserSettings
from ..providers import resolve_llm_config
from ..research import start_run

router = APIRouter()


class RunRequest(BaseModel):
    target: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=10, ge=1, le=30)
    strict: bool = False


def _summary(run: Run) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "target": run.target,
        "top_k": run.top_k,
        "strict": bool(run.strict),
        "progress_note": run.progress_note,
        "created_at": run.created_at.isoformat(),
    }


@router.post("/runs")
def create_run(
    body: RunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = resolve_llm_config(db.get(UserSettings, user.id))
    if cfg is None:
        raise HTTPException(
            503, "No LLM provider configured — add your API key in Settings first"
        )
    prof = db.get(Profile, user.id)
    if prof is None or not prof.data:
        raise HTTPException(400, "Complete your profile before starting a run")
    active = (
        db.query(Run)
        .filter(Run.user_id == user.id, Run.status.in_(["queued", "researching", "scoring"]))
        .count()
    )
    if active >= 2:
        raise HTTPException(429, "You already have 2 active runs; wait for them to finish")
    run = Run(user_id=user.id, target=body.target, top_k=body.top_k, strict=int(body.strict))
    db.add(run)
    db.commit()
    start_run(run.id, prof.data, body.target, body.top_k, body.strict, cfg)
    return {"id": run.id}


@router.get("/runs")
def list_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = (
        db.query(Run)
        .filter(Run.user_id == user.id)
        .order_by(Run.created_at.desc())
        .limit(50)
        .all()
    )
    return [_summary(r) for r in runs]


@router.get("/runs/{run_id}")
def get_run(
    run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    run = db.get(Run, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(404, "Run not found")
    out = _summary(run)
    out.update(
        results=run.results,
        portfolio_summary=run.portfolio_summary,
        error=run.error,
    )
    return out
