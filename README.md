# Fitness Hub

Unified personal health and fitness data hub for:

- WHOOP for recovery, sleep, strain, and body metrics
- Hevy for workout structure and exercise data
- MyFitnessPal for nutrition, hydration, and weight

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- APScheduler
- SQLite for local development, PostgreSQL for hosted deployment
- Jinja templates for the dashboard

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and fill in secrets.
   For local development, the default database is `sqlite:///./fitness.db`, so you do not need Postgres to get started.
4. Run the app:

```bash
uvicorn app.main:app --reload
```

## Hosted Setup

- Deploy the app using the included `Dockerfile`.
- Use Neon Postgres for `DATABASE_URL`.
- On Railway, set `ENABLE_SCHEDULER=false` and let GitHub Actions drive hosted WHOOP and Hevy syncs.
- Use [docs/deployment.md](docs/deployment.md) for the full Railway + Neon + GitHub Actions setup.

## Project Layout

- `app/` application code
- `alembic/` database migrations
- `scripts/mfp_bridge.py` local MyFitnessPal sync worker
- `scripts/run_mfp_sync.py` daytime-safe MyFitnessPal scheduler wrapper
- `scripts/install_mfp_launch_agent.sh` macOS launchd installer for the MFP bridge
- `docs/deployment.md` hosted deployment and automation guide
- `tests/` automated tests

## Notes

- WHOOP uses OAuth and supports webhooks plus reconciliation polling.
- This project currently defaults to polling-first behavior and does not actively process WHOOP webhooks unless explicitly enabled.
- Hevy requires a Pro account and uses an API key.
- MyFitnessPal is integrated through an unofficial personal-use bridge.
- On macOS, Safari cookie access may be blocked by system permissions. If that happens, log into MyFitnessPal in Chrome or Firefox and run `python3 scripts/mfp_bridge.py --browser chrome --days 90`.
- If browser cookie extraction still fails, export a `cookies.txt` file for `myfitnesspal.com` or copy a logged-in `Cookie` request header, then run `python3 scripts/mfp_bridge.py --cookie-file ~/Downloads/cookies.txt --days 90` or `python3 scripts/mfp_bridge.py --cookie-header 'name=value; other=value' --days 90`.
- To keep MyFitnessPal syncing automatically on your Mac, point `MFP_BRIDGE_BASE_URL` at your hosted app and run `./scripts/install_mfp_launch_agent.sh`.
