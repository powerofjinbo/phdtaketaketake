import io
import json
import re

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import engine as eng
from ..auth import get_current_user
from ..db import get_db
from ..models import Profile, User, UserSettings
from ..providers import resolve_llm_config, run_completion

router = APIRouter()

CV_PARSE_SYSTEM = """\
You parse a PhD applicant's CV text into a strict JSON profile. Extract ONLY
facts explicitly present in the CV — never infer or embellish. Output a
single ```json fenced block:

{
  "name": str or omit,
  "field": str (e.g. "physics", "biology", "cs") — infer only from explicit CV content,
  "undergrad_institution": str,
  "gpa_raw": number, "gpa_scale": "4.0"|"4.3"|"4.5"|"100"|"uk_honours",
  "research_direction": 1-2 sentence summary built strictly from the CV's stated research topics,
  "current_advisors": [{"id": "adv_001", "name": str, "institution": str}],
  "papers": [{"title": str, "journal": str, "journal_tier": 1-5 (4 if unsure),
              "author_position": int, "status": "published"|"accepted"|"submitted"|"preprint"|"in_prep",
              "year": int}],
  "experiences": [{"lab_pi_name": str, "lab_tier": 1-4 (3 if unsure),
                   "duration_months": int, "output_type": "paper"|"poster"|"thesis"|"none"}]
}

Omit any field the CV does not state. After the JSON block, list one warning
line per field you omitted or were unsure about, prefixed "WARN: ".
"""


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prof = db.get(Profile, user.id)
    return prof.data if prof else {}


@router.post("/profile/parse-cv")
def parse_cv(
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file")
    cfg = resolve_llm_config(db.get(UserSettings, user.id))
    if cfg is None:
        raise HTTPException(
            503, "No LLM provider configured — add your API key in Settings first"
        )
    raw = file.file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "PDF too large (max 10 MB)")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:10])
    except Exception:
        raise HTTPException(400, "Could not read that PDF")
    if len(text.strip()) < 100:
        raise HTTPException(
            400,
            "Could not extract text from this PDF (it may be a scanned image). "
            "Try an exported/text-based PDF.",
        )
    try:
        out = run_completion(cfg, CV_PARSE_SYSTEM, f"CV text:\n\n{text[:40000]}")
    except Exception as e:
        raise HTTPException(502, f"LLM provider error: {e}")
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", out, re.DOTALL)
    if not m:
        raise HTTPException(502, "CV parser returned no JSON — try again")
    try:
        profile = json.loads(m.group(1))
    except json.JSONDecodeError:
        raise HTTPException(502, "CV parser returned invalid JSON — try again")
    warnings = [
        line.strip()[5:].strip()
        for line in out.splitlines()
        if line.strip().startswith("WARN:")
    ]
    return {"profile": profile, "warnings": warnings}


@router.put("/profile")
def put_profile(
    body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        eng.StudentProfile(**body)  # validate against the engine's strict schema
    except Exception as e:
        raise HTTPException(422, f"Profile validation failed: {e}")
    prof = db.get(Profile, user.id)
    if prof is None:
        prof = Profile(user_id=user.id, data=body)
        db.add(prof)
    else:
        prof.data = body
    db.commit()
    return {"ok": True}
