# Environments

The SRS (section 12.2) requires three separate environments. This page describes how each one is used and what is configured today.

## Overview

| Environment | Purpose | Data | Status |
|---|---|---|---|
| Development | Local development and integration | Synthetic test data only | In use (Docker Compose) |
| Staging | Integration, QA and UAT | Synthetic or anonymized data | Not set up yet. Vercel preview deployments are a possible option. |
| Production | Actual deployment | Approved real user data | Planned on Vercel (see Hosting). Not created yet. |

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

## Hosting (Vercel)

The team decided to host on Vercel (free Hobby plan). Vercel builds from GitHub and does not use the Docker images. On the Hobby plan, only repositories in the owner's own GitHub account can be deployed, so the projects are created under the repository owner's Vercel account.

| Part | Planned Vercel project | Root directory | Notes |
|---|---|---|---|
| Frontend | `nexus-career` | `frontend` | Vite build. `frontend/vercel.json` rewrites all routes to `index.html`, so React routes work on refresh |
| Backend | `nexus-career-api` | `backend` | Django runs as a serverless function. Vercel finds it through `WSGI_APPLICATION` |
| Database | Hosted PostgreSQL (Neon) | n/a | Use the pooled connection string, because serverless functions open many short connections |

### Hosted environment variables

Set these in the Vercel dashboard. Never commit them.

| Variable | Project | Value |
|---|---|---|
| `VITE_API_BASE_URL` | Frontend | `https://<backend domain>/api/v1` |
| `DJANGO_DEBUG` | Backend | `false` |
| `DJANGO_SECRET_KEY` | Backend | Long random value (required when debug is off) |
| `DJANGO_ALLOWED_HOSTS` | Backend | The backend's domain |
| `CORS_ALLOWED_ORIGINS` | Backend | `https://<frontend domain>` |
| `STUDENT_EMAIL_DOMAIN` | Backend | `scds.saiuniversity.edu.in` |
| `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT` | Backend | From the hosted database |
| `PGSSLMODE` | Backend | `require` |
| `EMAIL_HOST` | Backend | SMTP server of the chosen mail provider |
| `EMAIL_PORT` | Backend | `587` |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Backend | SMTP login from the provider |
| `EMAIL_USE_TLS` | Backend | `true` |
| `DEFAULT_FROM_EMAIL` | Backend | The sender address shown on password reset emails |

### Migrations on the hosted database

Run from a developer machine with the hosted database details. Never commit or share the values.

```
docker compose run --rm --no-deps -e PGHOST=<host> -e PGPORT=5432 -e PGUSER=<user> -e PGPASSWORD=<password> -e PGDATABASE=<db> -e PGSSLMODE=require backend python manage.py migrate
```

`make backup` and `make restore` only work on the local database container.

### Known limits of serverless hosting

- The server disk is temporary, so uploaded resumes must be stored in private object storage, not in a local folder (SRS NFR-SCL-04, NFR-SEC-07).
- There are no persistent background processes.
- Django admin and API documentation pages need static-file handling to look styled.

### Rollback

- Vercel keeps earlier deployments. If a release breaks the site, open the project's Deployments list in the dashboard and promote the last working deployment.
- Database migrations are not rolled back by redeploying. Take a backup of the hosted database before applying a risky migration, and check the provider's own backup and restore options.

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

- **Backend job:** validates `docker-compose.yml`, starts PostgreSQL and Django in Docker, checks dependencies, runs `manage.py check`, checks for missing migrations, applies migrations and runs the tests.
- **Frontend job:** `npm ci`, a dependency audit report, lint and build.
- **Code Quality:** `ruff` on the backend for real errors.
- **Security:** a gitleaks secret scan and a report-only `pip-audit` of the backend packages. Also runs weekly.

A new push to a pull request cancels the older run for that PR. Runs on `main` are never cancelled.

Dependabot opens weekly pull requests for outdated backend, frontend, GitHub Actions and Docker dependencies. Merge small updates when the checks are green. Major version upgrades (Django, Python, Node) need testing first, so ignore them close to a deadline.

CI uses fake credentials from `.env.example`.

## Health check

`GET /api/v1/health/` returns `{"status": "ok"}` with a 200. It needs no login and makes no database call, so it only shows that the app is running. Use it for uptime checks.


## Logging

- The backend has no custom logging configuration. Django's defaults apply, so errors go to the console, and on Vercel they appear in the project's function logs.
- With `DJANGO_DEBUG=false`, users see a generic error page and never a stack trace (NFR-REL-02).
- Rules: never log passwords, tokens, reset links or resume text (NFR-SEC-10). When a password reset email fails, only the user id is logged (checked in the security review).
- CI prints the service logs when the backend job fails.

## Production server note

The Docker image runs Django's development server (`runserver`), so it is for local development and CI only. On Vercel the backend runs in Vercel's own runtime and this image is not used. If the hosting changes to a plain server, a production web server (for example gunicorn) must be added first.

## Still to define

- Backup schedule and retention period for the hosted database (the SRS requires a retention policy)
- Resume storage service
- Health-check endpoint (SRS 12.3, point 6)
- Structured logging and monitoring (SRS 12.3, point 7)