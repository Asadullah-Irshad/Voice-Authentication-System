# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] — 2026-08-15

A full hardening and productionization of the original prototype.

### Added
- **JWT bearer authentication** on every sensitive endpoint; the acting user is resolved
  from the signed token rather than trusted from the request body.
- **Rate limiting** on the auth endpoints to blunt brute-force attempts.
- **Per-file upload size caps** and strict extension validation.
- **Environment-driven configuration** via `pydantic-settings` (`.env` support).
- **Docker** support: `Dockerfile` (non-root) and `docker-compose.yml` with a healthcheck.
- **Continuous integration** via GitHub Actions (lint + format + tests).
- **Automated test suite** — 17 unit and API tests (`pytest`, pipeline mocked).
- **Documentation** — comprehensive `README`, `CONTRIBUTING.md`, `SECURITY.md`, and a
  screenshot gallery + product walkthrough GIF.
- `/api/health` liveness probe.

### Changed
- **Passwords are now hashed with bcrypt** (work factor 12) instead of stored in plaintext.
- **CORS** restricted to an explicit, env-driven allow-list (was wildcard `*`).
- Project layout reorganised: `Fronted/` → `frontend/`, `Backend/your_server/` →
  `backend/app/`, with a dedicated `tests/` package.
- Heavy ML imports (`torch`/`speechbrain`) are now lazy, so the app imports cheaply and is
  testable without the full ML stack.
- Minimum password length raised to 8 characters.
- Logging replaces stray `print` statements.

### Removed
- Committed build artifact (`Audio_Classification_Hub_v2.2.zip`).
- Hard-coded SMTP credentials and secrets.

### Security
- No plaintext passwords, no wildcard CORS, no secrets in source, brute-force protection,
  and upload hardening. See [SECURITY.md](SECURITY.md).

## [1.0.0] — initial prototype

- FastAPI backend with register/login (CSV store), voice enrollment pipeline
  (preprocess → ECAPA-TDNN embedding → averaging → inject → build `.whl`), individual and
  company modes, welcome email, and an animated multi-page frontend.
