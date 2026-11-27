# Anji Sprint 2 R1: Repository and Dependency Report

**Inspected:** 2 November 2026  
**Branch:** `feature/anji-r8-r9`

## Current repository findings

The checked-out branch contains the Django/DRF foundation and the Sprint 1 test and
OpenAPI scaffolding. Its `/api/v1/` URL registry is empty and it does not include the
feature models below. The local remote-tracking ref `origin/feature/database-schema`
contains an accounts app with a custom `User` and roles, plus recruiter `Company` and
`RecruiterProfile` models. That branch defines company states `PENDING`, `VERIFIED`, and
`REJECTED`, along with `verified_by` and `verified_at`. It is separate from the checked-out
branch and has not been integrated here.

| Area | Present in this checkout | R1 impact |
|---|---|---|
| User model | Checked-out branch uses Django's built-in `auth.User`; `origin/feature/database-schema` has `apps.accounts.User` | Need the team to confirm/integrate that branch before use |
| Roles | Checked-out fixtures use test-only Groups; database-schema branch has a `role` choice field | Role values exist on the separate branch, but no shared permission interface is present |
| Authentication | No project-specific authentication configuration or login/token implementation | Authentication behavior cannot be tested against Deepak's implementation |
| Shared permissions | No shared permission classes | IPC-only authorization cannot be implemented safely |
| Suspended-account state | No account status field/service | Suspended-user cases cannot be exercised |
| Recruiter/company | Database-schema branch has `Company` verification fields and `RecruiterProfile`; checked-out branch has no app/routes | Model exists on a separate branch, but endpoint integration requires that model branch and shared permissions |
| Alumni/proof | No models, proof submission, protected file access, or routes | No safe alumni verification integration |
| Audit | No audit service | Decisions cannot meet the required audit trail |
| API docs | drf-spectacular is configured; no product routes exist | No real verification operation can be documented yet |
| Test runner | pytest and pytest-django are configured; baseline fixtures/tests exist | Reusable foundation is available for integration when the real interfaces arrive |

## Implementation status

No Sprint 2 verification endpoint, model, status field, permission class, or audit system
was added. The master prompt requires agreement on status transitions and integration
with teammate-owned interfaces, and explicitly forbids creating replacements. Adding an
endpoint against Django's generic user model or test-only Groups would create an
unreviewed security contract and would not verify recruiters or alumni.

The independently reusable R8/R9 foundation remains available. The PostgreSQL-backed CI
workflow runs `pytest`, and OpenAPI will include endpoints once their actual routes are
registered.

## Interfaces required to proceed with R1

1. **Deepak:** production user model, role values, authentication mechanism, IPC/system
   admin permission classes, suspended-account behavior, audit service API, and the
   approved system-admin access policy.
2. **Charan:** recruiter/company models, recruiter-to-company relationship, ownership of
   verification status, allowed status values/transitions, and endpoint/service ownership.
3. **Nayana:** alumni model and user relationship, proof submission/storage interface,
   verification status ownership, and protected evidence retrieval mechanism.
4. **Team decision:** rejection-reason rules, re-verification behavior, status transitions,
   and the agreed recruiter and alumni API contracts.
5. **Sreehari:** review/approval process for any shared schema migration, if the agreed
   integration needs one.

Once those interfaces are present, the existing role fixtures should be adapted to the
real user/role model, then the authentication, role, suspended-user, object-access,
verification, persistence, and audit tests can be added against the real endpoints.
The prepared test matrix is in [`anji-s2-r1-test-plan.md`](anji-s2-r1-test-plan.md), and
the pending API documentation fields are in
[`anji-s2-r1-api-contract-draft.md`](anji-s2-r1-api-contract-draft.md).

## Checks attempted

From `backend/`, the baseline command collected five tests. Four passed. The database-backed
role fixture test errored during PostgreSQL setup because a server at `127.0.0.1:5432` was
not reachable in this environment. This does not establish anything about the missing
Sprint 2 integrations. The test suite needs to run again with PostgreSQL available, and
the R1 tests must wait for the interfaces listed above.

The four non-database baseline tests passed when rerun separately. OpenAPI validation
also passed and produced a valid schema with no paths, consistent with the empty route
registry.

After installing `backend/requirements/development.txt`, run the suite from `backend/`
with:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = "local-test-only"
pytest
```

