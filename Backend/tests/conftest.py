"""
Shared pytest fixtures.

Runtime data is redirected to a temporary directory (via env vars read by
``app.config.Settings``) *before* the app is imported, so tests never touch a
real ``data/`` folder. The heavy ML pipeline is mocked at the API boundary.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

# ── Isolate runtime data + deterministic secret BEFORE importing the app ──────
_TMP = tempfile.mkdtemp(prefix="ach_test_")
os.environ["DATA_DIR"] = str(Path(_TMP) / "data")
os.environ["WORKSPACES_DIR"] = str(Path(_TMP) / "workspaces")
os.environ["JWT_SECRET"] = "test-secret-key-not-for-production"
os.environ["EMAIL_ENABLED"] = "false"


@pytest.fixture
def client(monkeypatch):
    """A TestClient with the ML pipeline mocked so no models are needed."""
    from app import main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "clean_audio", lambda p: np.zeros(48000, dtype=np.float32))
    monkeypatch.setattr(main, "get_embedding", lambda a: np.ones(192, dtype=np.float32))
    monkeypatch.setattr(main, "inject_embedding", lambda master, ws: None)
    monkeypatch.setattr(main, "inject_company_embeddings", lambda emb, ws: None)

    def _fake_build(ws):
        whl = Path(ws) / "dist"
        whl.mkdir(parents=True, exist_ok=True)
        out = whl / "audioauth-1.0.0-py3-none-any.whl"
        out.write_bytes(b"PK\x03\x04 fake wheel")
        return str(out)

    monkeypatch.setattr(main, "build_whl", _fake_build)

    return TestClient(main.app)


@pytest.fixture
def wav_bytes():
    """Minimal fake audio payload (content is ignored — clean_audio is mocked)."""
    return b"RIFF....WAVEfake-audio-data"
