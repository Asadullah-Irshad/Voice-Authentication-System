"""
Voice Authentication System — FastAPI backend (v2).

Endpoints
    POST /api/register          create account            -> access_token
    POST /api/login             authenticate              -> access_token
    POST /api/process           enroll one voice          [auth]
    POST /api/process_company   enroll a team of voices   [auth]
    POST /api/verify            score a sample vs profile [auth]
    GET  /api/status            build status              [auth]
    GET  /api/download          download the built .whl   [auth]
    GET  /api/health            liveness probe

Security highlights over v1: bcrypt-hashed passwords, JWT bearer auth on every
sensitive route (the user is derived from the token, never trusted from the
request body), env-driven CORS allow-list, per-file upload size caps, and
rate-limited auth endpoints.
"""

import logging
import shutil
import uuid
from collections import defaultdict
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, FRONTEND_DIR, WORKSPACES_DIR, settings
from .database import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_whl_path,
    save_whl_path,
    user_exists,
)
from .email_service import send_welcome_email
from .pipeline.averaging import build_master
from .pipeline.builder import build_whl
from .pipeline.embedding import get_embedding
from .pipeline.injector import inject_company_embeddings, inject_embedding
from .pipeline.preprocess import clean_audio
from .rate_limit import auth_rate_limit
from .security import create_access_token, current_user_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ach")

ALLOWED_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
VERIFY_EXT = ALLOWED_EXT | {".webm", ".mp4"}
MAX_BYTES = settings.max_upload_mb * 1024 * 1024

WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Consistent JSON error envelope ───────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ── Static assets (css/js) mounted where the HTML expects them ───────────────
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _read_capped(upload: UploadFile) -> bytes:
    """Read an upload, rejecting anything over the configured size cap."""
    content = await upload.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            413, f"{upload.filename} exceeds the {settings.max_upload_mb} MB limit."
        )
    return content


def _validate_ext(filename: str, allowed: set[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type: {filename}")
    return ext


# ════════════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    auth_rate_limit(request)
    if not name.strip():
        raise HTTPException(400, "Name is required")
    if "@" not in email or "." not in email:
        raise HTTPException(400, "Invalid email address")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if user_exists(email):
        raise HTTPException(409, "Email already registered. Please log in.")

    username = name.strip().lower().replace(" ", "_")
    create_user(name=name, email=email, password=password, username=username)
    token = create_access_token(email)
    return JSONResponse(
        {
            "status": "ok",
            "message": "Account created",
            "username": username,
            "access_token": token,
            "token_type": "bearer",
        }
    )


@app.post("/api/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    auth_rate_limit(request)
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    return JSONResponse(
        {
            "status": "ok",
            "name": user["name"],
            "email": user["email"],
            "username": user["username"],
            "whl_ready": bool(user.get("whl_path")),
            "access_token": create_access_token(user["email"]),
            "token_type": "bearer",
        }
    )


# ════════════════════════════════════════════════════════════════════════════
#  ENROLL — single voice
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/process")
async def process_audio(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    email: str = Depends(current_user_email),
):
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "User not found. Please register first.")
    if not (settings.min_files <= len(files) <= settings.max_files):
        raise HTTPException(
            400,
            f"Please provide between {settings.min_files} and {settings.max_files} audio files.",
        )
    for f in files:
        _validate_ext(f.filename, ALLOWED_EXT)

    username = user["username"]
    build_id = uuid.uuid4().hex[:8]
    workspace = WORKSPACES_DIR / f"{username}_{build_id}"
    uploads_dir = workspace / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    voice_dir = DATA_DIR / username / "voices"
    voice_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for f in files:
        content = await _read_capped(f)
        dest = uploads_dir / Path(f.filename).name
        dest.write_bytes(content)
        (voice_dir / Path(f.filename).name).write_bytes(content)
        saved_paths.append(str(dest))

    try:
        audio_arrays, skipped = [], 0
        for p in saved_paths:
            try:
                audio_arrays.append(clean_audio(p))
            except ValueError as e:
                if "too short" in str(e).lower():
                    skipped += 1
                else:
                    raise
        if len(audio_arrays) < settings.min_files:
            raise ValueError(
                f"Only {len(audio_arrays)} valid audio files (>= 2s). "
                f"Minimum {settings.min_files} required."
            )

        import numpy as np

        embeddings = [get_embedding(a) for a in audio_arrays]
        master = build_master(embeddings)
        np.save(str(DATA_DIR / username / "embedding.npy"), master)

        inject_embedding(master, workspace)
        whl_path = build_whl(workspace)
        save_whl_path(email, whl_path)

        background_tasks.add_task(
            send_welcome_email, name=user["name"], email=email, whl_path=whl_path
        )
    except Exception as e:
        logger.exception("Pipeline failed")
        shutil.rmtree(workspace, ignore_errors=True)
        raise HTTPException(500, f"Pipeline failed: {type(e).__name__}: {e}") from e

    return JSONResponse(
        {
            "status": "ok",
            "message": "Voice embedding created and .whl built successfully",
            "build_id": build_id,
            "accepted_files": len(audio_arrays),
            "skipped_files": skipped,
        }
    )


# ════════════════════════════════════════════════════════════════════════════
#  ENROLL — company / multi-speaker
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/process_company")
async def process_company_audio(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    email: str = Depends(current_user_email),
):
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "User not found. Please register first.")

    person_files: dict[str, list[UploadFile]] = defaultdict(list)
    for f in files:
        parts = f.filename.split("/")
        if len(parts) != 2:
            raise HTTPException(400, f"Invalid path: {f.filename}. Expected PersonName/filename")
        person_name, actual = parts
        _validate_ext(actual, ALLOWED_EXT)
        person_files[person_name].append(f)

    if not person_files:
        raise HTTPException(400, "No valid audio files received.")
    for person, flist in person_files.items():
        if not (settings.min_files <= len(flist) <= settings.max_files):
            raise HTTPException(
                400,
                f"Person '{person}' has {len(flist)} files. "
                f"Must be between {settings.min_files} and {settings.max_files}.",
            )

    username = user["username"]
    build_id = uuid.uuid4().hex[:8]
    workspace = WORKSPACES_DIR / f"{username}_company_{build_id}"
    uploads_dir = workspace / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    company_embeddings, total_accepted, total_skipped = {}, 0, 0
    try:
        for person, flist in person_files.items():
            saved_paths = []
            for f in flist:
                content = await _read_capped(f)
                dest = uploads_dir / f"{person}_{Path(f.filename).name}"
                dest.write_bytes(content)
                saved_paths.append(str(dest))

            audio_arrays, skipped = [], 0
            for p in saved_paths:
                try:
                    audio_arrays.append(clean_audio(p))
                except ValueError as e:
                    if "too short" in str(e).lower():
                        skipped += 1
                    else:
                        raise
            if len(audio_arrays) < settings.min_files:
                raise ValueError(
                    f"Person '{person}' only has {len(audio_arrays)} valid files. "
                    f"Minimum {settings.min_files} required."
                )
            total_accepted += len(audio_arrays)
            total_skipped += skipped
            company_embeddings[person] = build_master([get_embedding(a) for a in audio_arrays])

        inject_company_embeddings(company_embeddings, workspace)
        whl_path = build_whl(workspace)
        save_whl_path(email, whl_path)

        background_tasks.add_task(
            send_welcome_email, name=user["name"], email=email, whl_path=whl_path
        )
    except Exception as e:
        logger.exception("Company pipeline failed")
        shutil.rmtree(workspace, ignore_errors=True)
        raise HTTPException(500, f"Pipeline failed: {type(e).__name__}: {e}") from e

    return JSONResponse(
        {
            "status": "ok",
            "message": "Company voice embeddings created and .whl built successfully",
            "build_id": build_id,
            "people": list(company_embeddings.keys()),
            "accepted_files": total_accepted,
            "skipped_files": total_skipped,
        }
    )


# ════════════════════════════════════════════════════════════════════════════
#  VERIFY
# ════════════════════════════════════════════════════════════════════════════
@app.post("/api/verify")
async def verify_voice(
    file: UploadFile = File(...),
    email: str = Depends(current_user_email),
):
    import os
    import tempfile

    import numpy as np

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "User not found. Please register first.")

    emb_path = DATA_DIR / user["username"] / "embedding.npy"
    if not emb_path.exists():
        raise HTTPException(404, "No registered voiceprint found. Complete onboarding first.")
    master = np.load(str(emb_path))

    ext = _validate_ext(file.filename, VERIFY_EXT)
    content = await _read_capped(file)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        test_emb = get_embedding(clean_audio(tmp_path))
    except Exception as e:
        raise HTTPException(422, f"Could not process audio: {e}") from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    denom = float(np.linalg.norm(master) * np.linalg.norm(test_emb))
    cosine = float(np.dot(master, test_emb)) / denom if denom > 0 else 0.0
    confidence = round(min(100, max(0, (cosine * 100) + 20)), 1)

    if confidence >= 82:
        label, matched, color, icon = "Strong Match", True, "green", "fa-shield-check"
    elif confidence >= 65:
        label, matched, color, icon = "Partial Match", True, "amber", "fa-circle-half-stroke"
    elif confidence >= 45:
        label, matched, color, icon = "Weak Match", False, "orange", "fa-triangle-exclamation"
    else:
        label, matched, color, icon = "No Match", False, "red", "fa-xmark-circle"

    return JSONResponse(
        {
            "status": "ok",
            "confidence": confidence,
            "cosine_score": round(cosine, 4),
            "label": label,
            "matched": matched,
            "color": color,
            "icon": icon,
        }
    )


# ════════════════════════════════════════════════════════════════════════════
#  STATUS / DOWNLOAD / HEALTH
# ════════════════════════════════════════════════════════════════════════════
@app.get("/api/status")
async def check_status(email: str = Depends(current_user_email)):
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "User not found")
    whl_path = get_whl_path(email)
    ready = bool(whl_path and Path(whl_path).exists())
    return JSONResponse(
        {
            "status": "ok",
            "whl_ready": ready,
            "name": user["name"],
            "email": email,
            "whl_filename": Path(whl_path).name if ready else None,
        }
    )


@app.get("/api/download")
async def download_whl(email: str = Depends(current_user_email)):
    if not get_user_by_email(email):
        raise HTTPException(404, "User not found")
    whl_path = get_whl_path(email)
    if not whl_path or not Path(whl_path).exists():
        raise HTTPException(404, "No .whl file found. Complete voice registration first.")
    return FileResponse(
        path=whl_path,
        filename=Path(whl_path).name,
        media_type="application/octet-stream",
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


# ════════════════════════════════════════════════════════════════════════════
#  FRONTEND PAGES
# ════════════════════════════════════════════════════════════════════════════
def _page(name: str) -> FileResponse:
    path = FRONTEND_DIR / name
    if not path.exists():
        raise HTTPException(404, f"Page not found: {name}")
    return FileResponse(str(path))


_PAGES = [
    "index.html",
    "auth.html",
    "onboarding-type.html",
    "onboarding-record.html",
    "onboarding-company.html",
    "onboarding-processing.html",
    "download.html",
]


def _make_page_handler(page_name: str):
    async def handler() -> FileResponse:
        return _page(page_name)

    return handler


for _p in _PAGES:
    _handler = _make_page_handler(_p)
    app.add_api_route(f"/{_p}", _handler, methods=["GET"])  # /index.html
    app.add_api_route(f"/{_p[:-5]}", _handler, methods=["GET"])  # /index


@app.get("/")
async def serve_index():
    return _page("index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
