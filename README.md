# Nexus Career

Nexus Career is a university careers platform for discovering jobs and internships and supporting student, recruiter, IPC, and alumni workflows.

The repository is under active development. Implemented increments include JWT authentication and role-based access, student and alumni profiles, recruiter/company verification, opportunity approval and discovery, profile-based eligibility checks, private PDF resume handling, platform applications and tracking, in-app notifications, alumni verification, and alumni referral workflows. Recruiter/IPC application review, broader administrative analytics, report exports, and email reminders remain follow-on work.

## Technology stack

| Area | Technology |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework |
| Authentication | Simple JWT |
| API documentation | drf-spectacular (OpenAPI, Swagger UI, ReDoc) |
| Database | PostgreSQL 17 |
| Frontend | React 19, TypeScript, React Router, Vite |
| Local infrastructure | Docker Compose |
| Quality checks | Django tests, pytest (development), Ruff, ESLint, TypeScript build |
| CI | GitHub Actions |

## Repository layout

```text
nexus-career/
├── .github/workflows/       # CI and code-quality workflows
├── backend/
│   ├── api/
│   │   ├── core/            # Shared API utilities, pagination
│   │   └── v1/              # Versioned API routes
│   ├── apps/
│   │   ├── accounts/        # Custom user model and JWT authentication
│   │   ├── students/        # Student profile API
│   │   ├── alumni/          # Alumni verification, directory and referral workflows
│   │   ├── recruiters/      # Company verification and recruiter opportunity workflows
│   │   ├── opportunities/   # Opportunity lifecycle, eligibility and discovery
│   │   ├── applications/    # Platform applications and status history
│   │   └── notifications/  # Per-user in-app notification inbox
│   ├── config/              # Django settings and entry points
│   ├── requirements/        # Runtime and development dependency sets
│   ├── tests/               # Cross-module backend tests
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── features/opportunities/
│   │   ├── mocks/            # Demo opportunity data; API integration pending
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
├── docs/                    # Project requirements and technical documentation
├── .env.example
└── docker-compose.yml
```

## Prerequisites

Install:

- Git
- Docker Desktop with Docker Compose
- Python 3.12 (for running Django directly on Windows/macOS/Linux)
- Node.js 24 and npm (for the Vite frontend)
- Visual Studio Code (recommended)

You do not need a host PostgreSQL installation when using the provided Docker Compose database service.

## Quick start: run the full application locally

### 1. Clone the repository

```bash
git clone https://github.com/Deepak392/nexus-career.git
cd nexus-career
```

### 2. Create your local environment file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Open `.env`. Replace the example passwords and local-only Django secret with values for your machine. Keep `.env` private; never commit it. If you change the PostgreSQL password, keep `POSTGRES_PASSWORD` and `PGPASSWORD` in sync for both Docker and host-side development.

### 3. Build and start PostgreSQL and Django

Make sure Docker Desktop is running, then run from the repository root:

```bash
docker compose up -d --build
```

Apply database migrations:

```bash
docker compose exec backend python manage.py migrate
```

Create an administrator account:

```bash
docker compose exec backend python manage.py createsuperuser
```

Backend URLs:

- Django: http://localhost:8000/
- Django admin: http://localhost:8000/admin/
- OpenAPI schema: http://localhost:8000/api/schema/
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

### 4. Start the frontend

Open a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite prints the local URL; the default is http://localhost:5173/.

The frontend uses the Django REST API for authentication, opportunity discovery, student applications, recruiter/IPC workflows, notifications, and alumni/referral workflows. Configure `VITE_API_BASE_URL` when the backend is not available at `http://localhost:8000/api/v1`.

## Run the backend directly in VS Code (database in Docker)

This workflow is useful when you want Python breakpoints and Django reloads in VS Code while keeping PostgreSQL in Docker.

Start only PostgreSQL from the repository root:

```bash
docker compose up -d db
```

Create and activate a virtual environment:

Windows PowerShell (from `backend/`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux (from `backend/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the development dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements/development.txt
```

The root `.env` file is loaded by Django. For host-side connections it uses `PGHOST=127.0.0.1` and `PGPORT=5433`, because Compose publishes PostgreSQL on port 5433.

From `backend/`, run:

```bash
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. Keep the backend terminal running and start the frontend in a separate terminal as described above.

## Backend API routes currently registered

| Route | Purpose |
|---|---|
| `POST /api/v1/auth/register/` | Student registration (configured university email domain) |
| `POST /api/v1/auth/login/` | Obtain JWT access and refresh tokens |
| `POST /api/v1/auth/refresh/` | Refresh an access token |
| `GET /api/v1/auth/me/` | Get the authenticated user's profile |
| `POST /api/v1/auth/logout/` | Blacklist a refresh token |
| `POST /api/v1/auth/password-reset/` | Request a one-time password reset link by email |
| `POST /api/v1/auth/password-reset/confirm/` | Validate a reset token and set a new password |
| `GET/POST/PUT/PATCH /api/v1/students/profile/` | Manage the authenticated student's profile |
| `GET/POST/PUT/PATCH /api/v1/alumni/profile/` | Manage the authenticated alumnus profile |
| `GET /api/v1/alumni/search/` | Search verified alumni |
| `POST /api/v1/alumni/graduation-proof/` | Submit private PDF graduation evidence |
| `GET /api/v1/alumni/ipc/pending-verification/` | List alumni awaiting IPC verification |
| `GET /api/v1/alumni/ipc/{id}/proof/` | Download proof (IPC only) |
| `POST /api/v1/alumni/ipc/{id}/verify/` | Verify an alumni profile (IPC only) |
| `POST /api/v1/alumni/ipc/{id}/reject/` | Reject an alumni profile with a reason (IPC only) |
| `GET/POST /api/v1/alumni/referral-requests/` | List own referrals or submit a student referral request |
| `GET /api/v1/alumni/referral-requests/{id}/` | Retrieve a referral visible to the requesting participant |
| `POST /api/v1/alumni/referral-requests/{id}/{action}/` | Accept, decline, request/respond to information, or mark referred |
| `GET /api/v1/alumni/referral-requests/{id}/resume/` | Download a referral resume (participants only) |
| `GET /api/v1/alumni/metrics/` | Read the authenticated alumnus's engagement metrics |
| `GET /api/v1/notifications/` | List the authenticated user's notifications |
| `POST /api/v1/notifications/{id}/read/` | Mark an owned notification as read |
| `GET /api/v1/opportunities/` | List published, unexpired opportunities |
| `GET /api/v1/opportunities/{id}/` | Retrieve a published opportunity |

Opportunity write and approval actions use the authenticated recruiter and IPC routes under `/api/v1/recruiters/` and `/api/v1/ipc/`. The public opportunity endpoints remain read-only and expose published, unexpired listings only.

## Tests and quality checks

Run the Django backend test suite:

```bash
# From the repository root, with Docker services running:
docker compose exec backend python manage.py test
```

Or run locally from `backend/` with the virtual environment activated:

```bash
python manage.py test
```

Optional pytest-based development tests:

```bash
# From backend/
pytest
```

Frontend checks:

```bash
# From frontend/
npm ci
npm run lint
npm run build
```

CI runs backend dependency verification, Django system checks, migration checks, backend tests, frontend lint, and the frontend production build for pull requests and pushes to `main`.

## Useful Docker commands

Run the stack:

```bash
docker compose up -d
```

View service status and logs:

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f db
```

Stop containers (keeps the database volume):

```bash
docker compose down
```

Delete the local database volume (destructive; removes local database data):

```bash
docker compose down -v
```

## Development workflow

1. Update your local `main` branch before starting work.
2. Create a focused branch such as `feature/<module-name>` or `fix/<issue-name>`.
3. Keep each change scoped to one module or concern.
4. Add/update tests and run the relevant checks.
5. Open a pull request against `main`; merge only after review and required CI checks pass.

## Configuration notes

- `POSTGRES_PASSWORD` is used by the PostgreSQL container.
- `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, and `PGPORT` configure Django's database connection.
- `STUDENT_EMAIL_DOMAIN` configures the allowed domain for student registration. The default is `scds.saiuniversity.edu.in`; confirm this with the university before production use.
- `CORS_ALLOWED_ORIGINS` configures allowed frontend development origins.
- `FRONTEND_BASE_URL` is the public frontend origin used to build password reset links.
- `PASSWORD_RESET_TIMEOUT` controls reset-link validity in seconds (default: 1800 / 30 minutes).
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` configure password-reset email delivery. The local example uses Django's console email backend, so the reset URL is printed in backend logs. Configure SMTP before deploying.
- `DJANGO_SECRET_KEY` must be a private, sufficiently long random value outside local debug development.

## Project status

Nexus Career is an active university software-engineering project. Refer to the SRS and the module-specific documentation in `docs/` for the intended product scope. The repository's implemented API surface is narrower than the full SRS and is being expanded incrementally. See [Sprint 1–3 delivery notes](docs/sprint-1-3-delivery.md) for implemented scope, SRS traceability, and remaining work.


## Student eligibility and applications

Students can maintain their academic profile and PDF resume at /profile. The opportunity detail page now checks CGPA, graduation year, degree programme, department, and required skills against the published criteria. It explains each matching, unmet, or missing requirement before enabling application.

Platform applications are submitted through the authenticated API and retain a private copy of the resume used at submission. Students can track their applications at /applications. External opportunities link directly to the recruiter's configured application URL; Nexus Career does not claim to track an external submission.

See docs/student-eligibility-and-applications.md for the API contract and workflow details.


## Alumni verification and referrals

Alumni can submit a private PDF graduation proof from their profile. IPC administrators review pending submissions in the IPC dashboard and can verify or reject a profile with a recorded reason. Only verified alumni who have enabled referral availability appear in the student directory.

Students can search the verified alumni directory and submit referral requests with a target opportunity URL, PDF resume and message. Alumni can accept or decline requests, ask for additional information, and mark accepted requests as referred. Both participants can view the request history; resume downloads are limited to the student and assigned alumnus. Referral events generate in-app notifications.

See [docs/alumni-referrals-and-verification.md](docs/alumni-referrals-and-verification.md) for the workflow and API details.


## Password recovery

The login page links to **Forgot password?**. Users enter the email address registered to their account and receive a one-time link to the frontend reset page. The API deliberately returns the same confirmation for registered and unregistered email addresses to avoid disclosing account membership.

Reset links expire after 30 minutes by default, are single-use, and are validated by Django's password-reset token generator. New passwords are checked against the configured Django password validators. After a successful reset, outstanding JWT refresh tokens for that account are blacklisted.

For local development, use the console email backend configured in `.env.example`. Submit the forgot-password form and inspect the backend output:

```powershell
docker compose logs --tail=100 backend
```

Open the `/reset-password?uid=...&token=...` URL printed in the email body. For production, set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, configure the SMTP variables, set `FRONTEND_BASE_URL` to the deployed frontend origin, and use HTTPS.
