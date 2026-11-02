# Anji's Sprint 1 Backend Work: R8 and R9 Status Report

**Report date:** 28 October 2026  
**Repository branch:** `feature/anji-r8-r9`  
**Local commit:** `caf96ef` — `feat: add Anji R8 and R9 foundation`

## Purpose and scope

This report describes only Anji's Sprint 1 responsibilities: **R8, the shared test
framework and fixtures**, and **R9, the OpenAPI and Swagger foundation**. It records the
implementation present in the repository and distinguishes completed setup from work
that still depends on a running database, approved team contracts, or other owners.

## 1. What has been built

### R8: test framework and fixtures

The backend now has a pytest configuration in `backend/pytest.ini`. It selects Django's
settings, discovers tests under `backend/tests/`, and enables concise failure reporting
and strict test markers. The documented full-suite command is `pytest` from the
`backend/` directory.

Reusable fixtures in `backend/tests/conftest.py` provide an API client, a generic user
factory, and role-specific user fixtures for Student, Recruiter, IPC Admin, Alumni, and
System Admin. The fixtures create synthetic test accounts. They use Django's built-in
user and group models as a **test-only adapter** while the production user and role
contracts are pending confirmation; they do not add or change a production user model.

Baseline tests in `backend/tests/test_foundation.py` cover the pagination settings,
role fixture distinction, schema endpoint response, and Swagger/ReDoc page responses.
The PostgreSQL database configuration is kept in Django settings so Django can create
an isolated test database when a local PostgreSQL service is available.

### R9: OpenAPI and Swagger foundation

The project uses `drf-spectacular` to generate OpenAPI documentation. The configured
endpoints are `/api/schema/` for the schema, `/api/docs/` for Swagger UI, and
`/api/redoc/` for ReDoc. API routes are mounted beneath `/api/v1/`.

The API route registry is intentionally empty because this checkout has no implemented
feature endpoints yet. The generated schema therefore reports no product paths instead
of presenting planned endpoints as implemented behavior.

The shared pagination class uses page-number pagination with a default page size of 20
and a maximum of 50. The API conventions document describes routing, pagination,
applicable status-code guidance, and how feature owners should document real endpoints.
It also records that authentication and the shared error response format still need
team agreement.

### Developer setup and documentation

The backend has a minimal Django/DRF project configuration, PostgreSQL environment
settings, base and development dependency lists, an environment-variable example, and
README instructions for tests and API documentation. `.gitignore` excludes local
environment files, virtual environments, and test artifacts.

## 2. Parts that are partially complete or pending

### PostgreSQL-backed test execution

Four non-database test cases passed. The database-backed role fixture test could not
complete because no PostgreSQL server was reachable at `127.0.0.1:5432`; the Docker
daemon was also unavailable. As a result, the full `pytest` run is not verified as
passing. The role factory test still needs to pass against an isolated PostgreSQL test
database.

### Role and authentication contracts

The fixture names cover all five planned roles, but their Group-based implementation is
temporary test scaffolding. Deepak and the supervisor still need to confirm the
production role representation and authentication mechanism. Permission tests cannot
be meaningful until the shared permission classes and protected endpoints exist.

### Endpoint documentation upkeep

The schema generator and interactive documentation pages are configured and validated,
but there are no feature endpoints to document yet. R9's ongoing responsibility is to
update the schema and endpoint descriptions as other owners add real routes in later
sprints.

### Shared error format and CI integration

The API conventions document records status-code guidance, but the shared error envelope
has not been approved. No global exception handler or invented response format was
added. The `pytest` command is documented for Isha's CI integration; the CI workflow
itself was not changed because Isha owns it.

### Other Sprint 1 team deliverables

The project configuration points to PostgreSQL, but database startup and migrations
have not been verified on a clean PostgreSQL instance. No application model migrations
were created because the feature models are not present. A health-check endpoint and
Docker/CI setup belong to Isha's work and are not included in Anji's R8/R9 scope.

### Push to the shared GitHub repository

The work is committed locally on `feature/anji-r8-r9` as `caf96ef`. The push to
`Deepak392/nexus-career` was rejected with HTTP 403 for the authenticated account
`anjeyulumpallaa04-pixel`. The branch has not been uploaded to the shared repository;
that account needs write access, or the code must be pushed to a fork.

## 3. Overall conclusion

Anji's R8/R9 foundation is implemented locally: the test runner and role fixtures are
defined, and OpenAPI, Swagger, ReDoc, versioned routing, pagination guidance, and
documentation instructions are in place. Four non-database checks and schema validation
passed. The work is **not fully verified or integrated** until the role fixture test
passes with PostgreSQL, shared role/auth/error contracts are confirmed, real endpoints
are documented as they arrive, and the branch is pushed for review.
