# Hosted Deployment

## Overview

This app is set up for a free-first deployment using:

- Koyeb for the FastAPI web service
- Neon for PostgreSQL
- GitHub Actions for hosted WHOOP and Hevy sync triggers

MyFitnessPal stays local for now and syncs from your Mac.

## 1. Push To GitHub

- Push this repository to a private GitHub repository.
- Keep `.env` out of the repository.

## 2. Create Neon Postgres

- Create a Neon project and copy the connection string.
- Use the pooled or direct `postgresql://...` URL as `DATABASE_URL`.

## 3. Create Koyeb App

- Create a new Web Service from the GitHub repository.
- Let Koyeb build from the included `Dockerfile`.
- Use the free instance type.
- Set the health check path to `/healthz`.
- Set the environment variables:
  - `APP_ENV=production`
  - `APP_BASE_URL=https://<your-koyeb-domain>`
  - `DATABASE_URL=<your-neon-url>`
  - `ENABLE_SCHEDULER=false`
  - `ENABLE_WHOOP_WEBHOOKS=false`
  - `INTERNAL_SYNC_TOKEN=<random-secret>`
  - `MFP_BRIDGE_SHARED_TOKEN=<random-secret>`
  - `WHOOP_CLIENT_ID=<your-whoop-client-id>`
  - `WHOOP_CLIENT_SECRET=<your-whoop-client-secret>`
  - `WHOOP_REDIRECT_URI=https://<your-koyeb-domain>/connect/whoop/callback`
  - `HEVY_API_KEY=<your-hevy-api-key>`

The container boot command is already defined in `scripts/start_server.sh` and runs:

- `alembic upgrade head`
- `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 4. Update WHOOP Redirect URI

- In the WHOOP developer dashboard, add the hosted callback URI:
  - `https://<your-koyeb-domain>/connect/whoop/callback`

## 5. Configure GitHub Actions Secrets

Add these repository secrets:

- `APP_BASE_URL=https://<your-koyeb-domain>`
- `INTERNAL_SYNC_TOKEN=<same-token-used-in-koyeb>`

The scheduled workflow in `.github/workflows/hosted-sync.yml` will then:

- wake the hosted app with `/healthz`
- trigger WHOOP reconcile
- trigger Hevy sync

## 6. Local MyFitnessPal Bridge

On your Mac, keep `.env` configured with:

- `MFP_BRIDGE_BASE_URL=https://<your-koyeb-domain>`
- `MFP_BRIDGE_SHARED_TOKEN=<same-token-used-in-koyeb>`
- `MFP_COOKIE_HEADER=...` or `MFP_COOKIE_FILE=...`
- `MFP_SYNC_WINDOW_DAYS=3`

Install the local scheduler:

```bash
./scripts/install_mfp_launch_agent.sh
```

This installs a `launchd` agent that runs every 30 minutes and only syncs between `8:00 AM` and `11:30 PM` in your configured timezone.
