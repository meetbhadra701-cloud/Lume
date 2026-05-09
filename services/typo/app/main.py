"""Lume FastAPI backend — main entry point."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment: repo-root .env first (override=False),
# then services/typo/.env if present (override=True).
# Must happen before importing any module that reads env vars.
from app.store.paths import repo_root  # noqa: E402

load_dotenv(repo_root() / ".env", override=False)
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import time  # noqa: E402
import logging  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lume API",
    description="Personalized reading-accessibility backend",
    version="0.1.0",
)

# CORS — read from env; defaults to localhost dev
_allowed_origins_raw = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
_allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers (rev. 4 fix 24) ─────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": str(exc.errors())}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An internal error occurred."}},
    )


# ── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Seed demo RNG + rebuild bandit posteriors from events."""
    from app.store.db import get_conn
    from app.store.paths import db_path

    # Ensure DB is initialized (schema applied)
    db_file = db_path()
    if not db_file.exists():
        logger.warning(
            "Database not found at %s. Run: python scripts/reset_db.py", db_file
        )
    else:
        # Rebuild bandit posteriors from events
        try:
            from app.ml.bandit import get_bandit
            with get_conn() as conn:
                bandit = get_bandit()
                bandit.rebuild_from_events(conn)
                bandit.seed_demo_user(42)
            logger.info("Bandit posteriors rebuilt from events; demo RNG seeded.")
        except Exception as exc:
            logger.warning("Bandit startup failed (non-fatal): %s", exc)

    # Warm up textstat so first request doesn't take 9s
    try:
        import textstat
        textstat.flesch_kincaid_grade("warmup text for initialization purposes only")
        logger.info("textstat warmed up.")
    except Exception as exc:
        logger.warning("textstat warmup failed (non-fatal): %s", exc)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    return {"ok": True, "timestamp": int(time.time() * 1000)}


# Import and include API router
from app.api.routes import router as api_router  # noqa: E402

app.include_router(api_router)
