# Nexus Career

**Nexus Career** is a centralized placement and internship management platform designed to streamline career services within a university ecosystem.

The platform provides a unified system for managing student profiles, placement and internship opportunities, applications, alumni engagement, referrals, notifications, and career analytics.

---

## Overview

University placement processes often involve multiple disconnected systems for student information, job opportunities, applications, communication, and alumni engagement.

Nexus Career addresses this fragmentation through a modular platform that provides a common interface for students, alumni, recruiters, and university administrators.

The system is being developed with a focus on **modularity, maintainability, scalability, security, and automated software delivery**.

---

## Key Capabilities

* **User & Account Management** — Authentication, authorization, and role-based access.
* **Student Profiles** — Centralized academic and career information.
* **Placement Management** — Management of placement opportunities and applications.
* **Internship Management** — Internship opportunities and application tracking.
* **Alumni Network** — Alumni profiles and student-alumni engagement.
* **Referral Management** — Management and tracking of referrals.
* **Notifications** — Centralized application and system notifications.
* **Analytics** — Placement, internship, and application insights.
* **Document Management** — Management of resumes, offer letters, alumni profiles, and company assets.

---

## Architecture

The project follows a modular architecture with a Django-based backend and a dedicated frontend application.

```text
                        ┌─────────────────────┐
                        │       Frontend      │
                        │  React / Next.js    │
                        └──────────┬──────────┘
                                   │
                                   │ REST API
                                   ▼
                        ┌─────────────────────┐
                        │       Backend       │
                        │       Django        │
                        └──────────┬──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
       ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
       │ PostgreSQL  │      │   Celery    │      │    Media    │
       │  Database   │      │ Background  │      │  Documents  │
       │             │      │    Tasks    │      │             │
       └─────────────┘      └─────────────┘      └─────────────┘
```

---

## Repository Structure

```text
nexus-career/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── cd.yml
│   │   └── code-quality.yml
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   │
│   └── PULL_REQUEST_TEMPLATE.md
│
├── backend/
│   ├── config/
│   │   └── settings/
│   │
│   ├── apps/
│   │   ├── accounts/
│   │   ├── core/
│   │   ├── placement/
│   │   ├── alumni/
│   │   ├── referrals/
│   │   ├── notifications/
│   │   └── analytics/
│   │
│   ├── templates/
│   ├── static/
│   ├── media/
│   ├── requirements/
│   └── tests/
│
├── frontend/
├── docs/
├── docker/
├── scripts/
│
├── .gitignore
├── CONTRIBUTING.md
├── docker-compose.yml
├── Makefile
├── LICENSE
└── README.md
```

The backend is organized into independent Django applications to keep domain-specific functionality isolated and maintainable.

---

## Backend Modules

| Module          | Responsibility                                     |
| --------------- | -------------------------------------------------- |
| `accounts`      | User accounts, authentication, and authorization   |
| `core`          | Shared application functionality                   |
| `placement`     | Placement opportunities and application management |
| `alumni`        | Alumni profiles and engagement                     |
| `referrals`     | Referral creation and tracking                     |
| `notifications` | Application and system notifications               |
| `analytics`     | Placement and career-related analytics             |

Individual Django applications follow a consistent internal structure containing models, serializers, views, URLs, permissions, services, selectors, signals, tasks, constants, exceptions, and tests.

---

## Technology Stack

### Backend

* Python
* Django
* Django REST Framework
* Celery

### Frontend

* TypeScript
* React / Next.js
* Tailwind CSS

### Database

* PostgreSQL

### Infrastructure

* Docker
* Docker Compose
* GitHub Actions
* CI/CD

### Testing & Quality

* Pytest
* Automated test suites
* Automated code-quality checks

---

## Development Setup

### Prerequisites

Ensure the following are installed:

* Python
* Node.js
* PostgreSQL
* Docker
* Git

### Clone the Repository

```bash
git clone https://github.com/Deepak392/nexus-career.git
cd nexus-career
```

### Backend Setup

```bash
cd backend
```

Create and activate a virtual environment:

**Windows**

```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

Install development dependencies:

```bash
pip install -r requirements/development.txt
```

Use `backend/.env.example` as the list of local environment variables. Django reads
environment variables directly and does not load `.env` files itself; export those
values in your shell or use a local environment tool. For local development, set
`DJANGO_DEBUG=true` and a local-only `DJANGO_SECRET_KEY` before starting Django. When
`DJANGO_DEBUG` is false, Django refuses to start without an explicit secret key. Do not
commit secrets.

Run database migrations:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

---

## Docker

The project includes Docker configuration for running the application in a containerized development environment.

Build and start the services:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Stop the services:

```bash
docker compose down
```

---

## Testing

Run the backend test suite from `backend/` with:

```bash
pytest
```

The tests use PostgreSQL, matching the development database. Start a local PostgreSQL
instance and set `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST`, and `PGPORT` before
running pytest. For a local PowerShell session, also set:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = "local-development-only"
```

Django creates and destroys a separate test database; never point test settings at
production data. The configured PostgreSQL user must be allowed to create databases;
Django uses a separate `test_<PGDATABASE>` database. Tests are in `backend/tests/`;
role fixtures are test helpers only and do not define the production role model or
permissions.

### API schema and interactive docs

Start the backend with `python manage.py runserver` from `backend/`. The OpenAPI schema
is at `/api/schema/`, Swagger UI at `/api/docs/`, and ReDoc at `/api/redoc/`. API routes
are versioned under `/api/v1/`. Only registered routes appear in the schema; no product
endpoints are present until their owning modules implement them. Authentication and the
shared error contract still require team agreement and are documented as pending in
[`docs/api-conventions.md`](docs/api-conventions.md).

---

## Development Workflow

Development follows a feature-branch and pull-request workflow.

```text
main
│
├── feature/<feature-name>
├── fix/<issue-name>
└── docs/<change>
```

Create a feature branch:

```bash
git checkout -b feature/<feature-name>
```

Commit changes using descriptive messages:

```bash
git add .
git commit -m "feat: add internship application tracking"
```

Push the branch:

```bash
git push origin feature/<feature-name>
```

Open a Pull Request against `main` after completing development and testing.

---

## CI/CD

GitHub Actions is used to automate development workflows.

The repository includes workflows for:

* Continuous Integration
* Continuous Deployment
* Code-quality checks

Workflow definitions are maintained under:

```text
.github/workflows/
```

---

## Environment Configuration

Environment-specific configuration should not be committed to the repository.

Create a local environment file based on:

```text
backend/.env.example
```

Sensitive credentials, database passwords, API keys, and other secrets must remain outside version control.

---

## Project Documentation

Project documentation is maintained in:

```text
docs/
```

This directory is intended for system design documentation, architecture decisions, API documentation, development guidelines, and other project-level technical documentation.

---

## Contributing

Contributions should follow the development workflow and project conventions defined in `CONTRIBUTING.md`.

Before submitting a Pull Request:

1. Create a dedicated branch.
2. Implement the required changes.
3. Add or update tests where applicable.
4. Run the test suite.
5. Run code-quality checks.
6. Submit a Pull Request with a clear description of the changes.

---

## Project Status

**Status:** Active Development

Nexus Career is being developed as a Software Engineering project at **Sai University**.

The current repository contains the foundational project architecture and development structure. Individual modules and features are being implemented incrementally.

---

## License

This project is licensed under the terms specified in the [`LICENSE`](LICENSE) file.
