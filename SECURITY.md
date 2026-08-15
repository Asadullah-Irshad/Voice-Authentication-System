# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability, please **do not open a public issue**.
Instead, email the maintainer with:

- a description of the issue,
- steps to reproduce,
- the potential impact.

You can expect an acknowledgement within a few days. Please give a reasonable
window to address the issue before any public disclosure.

## Security features in this project

- Passwords hashed with **bcrypt** (work factor 12); plaintext is never stored.
- **JWT bearer tokens** authenticate every sensitive endpoint; the acting user
  is derived from the signed token, not from client-supplied fields.
- **CORS** is restricted to an explicit, env-driven allow-list.
- Upload endpoints enforce **file-type and size limits**.
- Auth endpoints are **rate-limited** against brute-force attacks.
- All secrets are read from the **environment**, never hard-coded.

## Hardening checklist for production

- [ ] Set a strong, unique `JWT_SECRET`.
- [ ] Restrict `CORS_ORIGINS` to your real front-end origin(s).
- [ ] Serve the app behind HTTPS (TLS terminating proxy).
- [ ] Migrate the CSV user store to a real database.
- [ ] Run the container as the provided non-root user (default in the Dockerfile).
- [ ] Keep dependencies patched (`pip list --outdated`).
