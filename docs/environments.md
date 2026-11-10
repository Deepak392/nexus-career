# Environments

The SRS (section 12.2) requires three separate environments. This page describes how each one is used and what is configured today.

## Overview

| Environment | Purpose | Data | Status |
|---|---|---|---|
| Development | Local development and integration | Synthetic test data only | In use (Docker Compose) |
| Staging | Integration, QA and UAT | Synthetic or anonymized data | Not set up yet (needs hosting decision) |
| Production | Actual deployment | Approved real user data | Not set up yet (needs hosting decision) |

**Rule:** real student resumes and personal information must not be copied into development or staging without an approved and secure process.

## Development (local)

1. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`.
2. Run `make up` (or `docker compose up --build`).
3. In a second terminal run `make migrate`.
4. Open http://localhost:5173 (frontend) and http://localhost:8000 (backend).

Run every `make` command from the project folder.

## Configuration

Settings are read from environment variables, so no code changes are needed between environments.

| Variable | Purpose | Local default |
|---|---|---|
| `POSTGRES_PASSWORD` | Database password (required) | none, set it in `.env` |
| `DJANGO_DEBUG` | Debug mode | `true` |
| `DJANGO_SECRET_KEY` | Django secret key. Required when debug is off. | empty (Django uses a local-only key) |
| `DJANGO_ALLOWED_HOSTS` | Hosts Django will serve | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Frontend addresses allowed to call the API | `http://localhost:5173,http://localhost:3000` |
| `STUDENT_EMAIL_DOMAIN` | Allowed student email domain | `scds.saiuniversity.edu.in` |
| `VITE_API_BASE_URL` | Backend API address used by the frontend | `http://localhost:8000/api/v1` |

The backend reads its database connection from `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` and `PGPORT`. Docker Compose sets these.

## Production requirements (proposed)

- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY` set to a long random value stored outside the repository
- `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` set to the real domains
- HTTPS and security headers enabled
- A production web server instead of Django's `runserver`
- Secrets stored in the hosting platform, never in Git
- Daily automated database backups (SRS NFR-REL-05)

The hosting platform has not been chosen yet. This list will be updated when it is.

## Database backup and restore

These commands work against the local database container.

| Command | What it does |
|---|---|
| `make backup` | Saves a dump to `backups/latest.dump` |
| `make restore` | Replaces the current tables with the dump |

Backups are ignored by Git (`backups/` is in `.gitignore`). A dump can contain personal data, so never commit or share one.

Restore test, local only:

1. `make backup`
2. Wipe the local schema:
   `docker compose exec -T db psql -U nexus_user -d nexus_career -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`
3. `make restore`
4. `make migrate` should report no pending migrations.

Never run the wipe command outside your own laptop.

## Continuous integration

On every pull request into `main`, GitHub Actions runs:

- **Backend job:** starts PostgreSQL and Django in Docker, checks dependencies, runs `manage.py check`, checks for missing migrations, applies migrations and runs the tests.
- **Frontend job:** `npm ci`, a dependency audit report, lint and build.
- **Code Quality:** `ruff` on the backend for real errors.

CI uses fake credentials from `.env.example`.

## Still to define

- Hosting platform for staging and production
- Deployment pipeline (`cd.yml`) and rollback procedure
- Health-check endpoint
- Retention and deletion policy for backups (the SRS requires one)