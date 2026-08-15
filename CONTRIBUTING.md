# Contributing

Thanks for your interest in improving Voice Authentication System! 🎙️

## Getting set up

```bash
git clone https://github.com/asadullahirshad3/Voice-Authentication-System.git
cd Voice-Authentication-System
python -m venv .venv && source .venv/bin/activate
pip install -r Backend/requirements-dev.txt
cp .env.example .env
```

## Before you open a PR

Run the full local check — the same steps CI runs:

```bash
ruff check backend        # lint
ruff format backend       # format
pytest                    # tests
```

All three must pass. Please add or update tests for any behaviour you change.

## Guidelines

- Keep pull requests focused; one logical change per PR.
- Match the existing style — `ruff format` handles formatting for you.
- Write clear commit messages (imperative mood: "Add X", "Fix Y").
- Never commit secrets or a real `.env` file.
- Update the README when you add or change user-facing behaviour.

## Reporting bugs

Open an issue with steps to reproduce, expected vs actual behaviour, and your
environment (OS, Python version). For security issues, see
[SECURITY.md](SECURITY.md) instead of filing a public issue.
