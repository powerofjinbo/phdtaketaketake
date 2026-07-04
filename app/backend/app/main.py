from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .db import Base, engine
from .routes import auth, profile, runs, settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PhDTake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(runs.router)
app.include_router(settings.router)


@app.get("/health")
def health():
    return {"ok": True}
