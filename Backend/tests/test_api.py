"""End-to-end API tests using FastAPI's TestClient (pipeline mocked)."""


def _register(client, email="alice@example.com"):
    return client.post(
        "/api/register",
        data={"name": "Alice Example", "email": email, "password": "supersecret1"},
    )


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_returns_token(client):
    r = _register(client)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_register_rejects_short_password(client):
    r = client.post(
        "/api/register",
        data={"name": "Bob", "email": "bob@example.com", "password": "short"},
    )
    assert r.status_code == 400


def test_duplicate_register_conflicts(client):
    _register(client, "dupe@example.com")
    r = _register(client, "dupe@example.com")
    assert r.status_code == 409


def test_login_and_wrong_password(client):
    _register(client, "carol@example.com")
    ok = client.post(
        "/api/login",
        data={"email": "carol@example.com", "password": "supersecret1"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post(
        "/api/login",
        data={"email": "carol@example.com", "password": "nope"},
    )
    assert bad.status_code == 401


def test_protected_endpoint_requires_auth(client):
    # No Authorization header -> 403 from HTTPBearer.
    r = client.get("/api/status")
    assert r.status_code in (401, 403)


def test_process_and_download_flow(client, wav_bytes):
    token = _register(client, "dave@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = [("files", (f"s{i}.wav", wav_bytes, "audio/wav")) for i in range(5)]
    proc = client.post("/api/process", files=files, headers=headers)
    assert proc.status_code == 200, proc.text
    assert proc.json()["accepted_files"] == 5

    status = client.get("/api/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["whl_ready"] is True

    dl = client.get("/api/download", headers=headers)
    assert dl.status_code == 200
    assert dl.content.startswith(b"PK")


def test_process_rejects_too_few_files(client, wav_bytes):
    token = _register(client, "erin@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    files = [("files", ("only.wav", wav_bytes, "audio/wav"))]
    r = client.post("/api/process", files=files, headers=headers)
    assert r.status_code == 400
