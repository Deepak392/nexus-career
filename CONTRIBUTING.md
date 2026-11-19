# Contributing to Nexus Career

Thanks for contributing! Please follow these rules so the project stays easy to build, test and deploy.

## 1. Local setup

1. Clone the repo and open the project folder.
2. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD` to any password for your own laptop.
3. Start everything with `docker compose up --build` (or `make up`).
4. Apply migrations in a second terminal with `docker compose exec backend python manage.py migrate` (or `make migrate`).
5. Open http://localhost:8000.

Never commit `.env`. It is listed in `.gitignore`.

## 2. Branches

Never work directly on `main`. Create a branch from an up-to-date `main`:

- `feature/<name>` for new features
- `fix/<name>` for bug fixes
- `docs/<name>` for documentation

## 3. Commit messages

Use short, descriptive messages with a prefix:

- `feat:` new feature
- `fix:` bug fix
- `chore:` setup or maintenance
- `docs:` documentation
- `ci:` pipeline changes

Example: `feat: add internship application tracking`

## 4. Pull requests

1. Push your branch and open a pull request into `main`.
2. Fill in the PR template checklist.
3. Wait for the CI and Code Quality checks to pass.
4. Request a review from a teammate. Do not merge your own PR without a review.
5. Merge using "Create a merge commit".

## 5. Dependencies

If your code needs a new Python package, add it to `backend/requirements.txt` in the same PR, with a pinned version. Otherwise Docker and CI will fail for everyone.

## 6. Database changes

If you change a model, create the migration and commit it in the same PR. CI fails when a migration is missing.

## 7. Secrets and security

- Never commit passwords, tokens or `.env` files.
- Keep secrets in environment variables.
- Do not put real student data in development or test environments.

## 8. Working with CI


Every pull request into `main` runs these checks. All of them must pass before you ask for a merge.

| Check | What it does | If it fails |
|---|---|---|
| CI / Backend | Validates `docker-compose.yml`, starts PostgreSQL and Django in Docker, checks required packages, runs `manage.py check`, checks for missing migrations, applies migrations and runs the tests | Open the failed step. Common causes: a package missing from `requirements`, or a model change without a migration (run `make makemigrations`) |
| CI / Frontend | `npm ci`, dependency audit report, lint and build | Run `npm run lint` and `npm run build` in `frontend/` and fix the errors |
| Code Quality | Runs `ruff` on the backend and fails on real errors | Fix the reported lines |
| Security | Scans the history for committed secrets (gitleaks) and reports vulnerable backend packages (pip-audit) | See the secrets note below |

Good to know:

- A new push to a pull request cancels the older CI run for that PR. Runs on `main` are never cancelled.
- Dependabot opens weekly pull requests for outdated packages. Merge small patch updates when the checks are green. Do not merge major version upgrades close to a deadline without testing them.
- If the secret scan finds a key or password, remove it from the code **and replace the key**. Anything committed once must be treated as leaked, even if you delete it later.

## 9. Useful commands

- `make up`: build and start everything
- `make down`: stop everything
- `make migrate`: apply migrations
- `make test`: run the tests
- `make clean`: stop everything and delete your local database (use with care)

`make` is optional. On Windows install it with `winget install ezwinports.make`. The plain `docker compose` commands also work.