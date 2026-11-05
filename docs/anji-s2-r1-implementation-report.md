# Nexus Career — Sprint 2 (S2) R1 Implementation Report

**Author:** Anji (IPC Administration, QA, API Documentation)  
**Branch:** `feature/anji-s2-r1`  
**Base commit (from `origin/main`):** `b1983e5`  
**Merge commit (Nayana's alumni branch):** `8d5a7ea`  
**Date:** 2026-11-06  

---

## 1. Scope

This report covers all S2 R1 deliverables assigned to Anji:

| ID | Deliverable | Status |
|----|-------------|--------|
| D1 | `IsIPCAdmin` shared permission class | ✅ Implemented |
| D2 | Audit dispatch boundary (`log_verification_audit`) | ✅ Implemented (in-memory; real DB backend deferred) |
| D3 | Recruiter verification endpoint | ✅ Implemented |
| D4 | Alumni verification endpoint | ✅ Implemented |
| D5 | Auth & permission test suite (8 tests) | ✅ Implemented |
| D6 | Verification workflow test suite (11 tests) | ✅ Implemented |
| D7 | `requirements/base.txt` updated with `simplejwt` | ✅ Done |
| D8 | `docs/` S2 implementation report | ✅ This document |
| D9 | Docs: dependency report, test plan, API contract | ✅ Created in prior step |

---

## 2. Files Created

| File | Purpose |
|------|---------|
| `backend/api/core/permissions.py` | `IsIPCAdmin`, `IsSystemAdmin` permission classes |
| `backend/api/core/audit.py` | `log_verification_audit()`, `get_audit_logs()`, `clear_audit_logs()` |
| `backend/apps/recruiters/serializers.py` | `RecruiterVerificationSerializer`, `RecruiterVerificationResponseSerializer` |
| `backend/tests/test_auth_and_permissions.py` | 8 auth/permission tests (A01, A02, A04, A05, P01, P02, P03, P06) |
| `backend/tests/test_verification_workflows.py` | 11 workflow tests (V01–V07 recruiter, V08–V12 alumni) |

---

## 3. Files Modified

| File | Change |
|------|--------|
| `backend/config/settings.py` | Conflict resolved (AUTH_USER_MODEL); SQLite fallback via `DJANGO_DB_ENGINE` env var |
| `backend/api/v1/urls.py` | Added recruiter + alumni admin verify routes; merged Nayana's student/alumni includes |
| `backend/apps/alumni/serializers.py` | Added `AlumniVerificationSerializer`, `AlumniVerificationResponseSerializer`; fixed `get_full_name` |
| `backend/apps/alumni/views.py` | Added `AlumniVerificationView` (IPC admin verification workflow) |
| `backend/apps/recruiters/views.py` | Added `RecruiterVerificationView` (IPC admin verification workflow) |
| `backend/apps/accounts/serializers.py` | Extended `allowed_domains` to include `@scds.saiuniversity.edu.in` (Deepak's test required it) |
| `backend/tests/conftest.py` | Added fixtures: `jwt_auth_headers`, `reset_audit_log_store`, `company_factory`, `pending_company`, `pending_recruiter`, `pending_alumni_profile`; upgraded `role_user_factory` |
| `backend/tests/test_foundation.py` | Updated schema assertion to `len(schema["paths"]) > 0` (routes now populated) |
| `backend/requirements/base.txt` | Added `djangorestframework-simplejwt>=5.3,<6` |

---

## 4. API Endpoints Implemented

### 4.1 Recruiter Verification

```
POST /api/v1/admin/recruiters/{id}/verify/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "VERIFIED" | "REJECTED",
  "reason": "string (required when status=REJECTED)"
}
```

**Permission:** `IsAuthenticated` + `IsIPCAdmin`  
**Atomic:** Yes (`transaction.atomic()`)  
**Audit:** `log_verification_audit("recruiter_verification", ...)` on success only  
**Allowed transitions:** `PENDING → VERIFIED`, `PENDING → REJECTED`  

**Success response (200):**
```json
{
  "id": 1,
  "company_name": "Acme Corp",
  "verification_status": "VERIFIED",
  "verified_by": 42,
  "verified_at": "2026-11-06T10:00:00Z"
}
```

### 4.2 Alumni Verification

```
POST /api/v1/admin/alumni/{id}/verify/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "VERIFIED" | "REJECTED",
  "reason": "string (required when status=REJECTED)"
}
```

**Permission:** `IsAuthenticated` + `IsIPCAdmin`  
**Atomic:** Yes (`transaction.atomic()`)  
**Audit:** `log_verification_audit("alumni_verification", ...)` on success only  
**Allowed transitions:** `PENDING → VERIFIED`, `PENDING → REJECTED`  
**Note (PROPOSED):** `verified_by` and `verified_at` fields not yet present on `AlumniProfile` model (Nayana's domain). Added at view layer; pending confirmation from Nayana and team to add to model.

---

## 5. Test Results

```
============================= test session starts =============================
platform win32 — Python 3.13.7, pytest-8.4.2
collected 24 items (Anji's tests) + 12 items (Deepak's account tests)

24 passed in 13.94s   (tests/)
12 passed in 8.29s    (apps/accounts/tests.py)
Total: 36 passed, 0 failed
```

### 5.1 Auth & Permission Tests (`test_auth_and_permissions.py`)

| Test ID | Scenario | Result |
|---------|----------|--------|
| A01 | Unauthenticated → 401 | ✅ PASS |
| A02 | Invalid JWT → 401 | ✅ PASS |
| A04 | Student role → 403 | ✅ PASS |
| A05 | Recruiter role (own company) → 403 | ✅ PASS |
| P01 | Alumni role → 403 | ✅ PASS |
| P02 | System admin → 403 (role isolation policy) | ✅ PASS |
| P03 | Inactive/suspended account → 403 | ✅ PASS |
| P06 | Authorized IPC admin → 200 | ✅ PASS |

### 5.2 Verification Workflow Tests (`test_verification_workflows.py`)

| Test ID | Scenario | Result |
|---------|----------|--------|
| V01 | IPC admin verifies pending recruiter → 200 | ✅ PASS |
| V02 | IPC admin rejects pending recruiter with reason → 200 | ✅ PASS |
| V03 | Rejection without reason → 400 | ✅ PASS |
| V04 | Nonexistent recruiter ID → 404 | ✅ PASS |
| V05 | Disallowed status transition (VERIFIED → REJECTED) → 400 | ✅ PASS |
| V06 | Unsupported decision value → 400 | ✅ PASS |
| V07 | Audit event recorded on successful recruiter verification | ✅ PASS |
| V08 | IPC admin verifies pending alumnus → 200 | ✅ PASS |
| V09 | IPC admin rejects pending alumnus with reason → 200 | ✅ PASS |
| V10 | Alumni rejection without reason → 400 | ✅ PASS |
| V11 | Nonexistent alumnus ID → 404 | ✅ PASS |
| V12 | Disallowed alumni status transition → 400 | ✅ PASS |

---

## 6. Architecture Decisions

### 6.1 `IsIPCAdmin` Permission Class

Placed in `backend/api/core/permissions.py` (not `apps/accounts/`) to avoid modifying Deepak's domain while still being shared across all IPC admin endpoints.

```python
class IsIPCAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and getattr(request.user, "role", None) == User.Role.IPC_ADMIN
        )
```

**`SYSTEM_ADMIN` is explicitly excluded** from IPC verification — consistent with the project requirement that separates system-level and IPC-level administration.

### 6.2 Audit Service Boundary

`backend/api/core/audit.py` implements an in-memory log store for testing. When Deepak provides a real `AuditLog` model and service, only the body of `log_verification_audit()` needs updating. All view integrations and test assertions remain unchanged.

### 6.3 SQLite Test Fallback

Added to `backend/config/settings.py`:
```python
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DJANGO_DB_ENGINE", "django.db.backends.postgresql"),
        ...
    }
}
```

CI continues to use PostgreSQL. Local developers set `DJANGO_DB_ENGINE=django.db.backends.sqlite3` to run tests without Docker.

---

## 7. Known Limitations & Pending Items

| Item | Description | Dependency |
|------|-------------|------------|
| Audit DB backend | `log_verification_audit()` currently writes to in-memory list, not DB | Deepak to provide `AuditLog` model/service |
| `AlumniProfile.verified_by` / `verified_at` | Not yet on the model; returned from view layer only | Nayana to add fields (or confirm alternative) |
| Deepak's shared permission classes | If Deepak adds `IsIPCAdmin` to `apps/accounts/`, re-export from `api/core/permissions.py` | Deepak |
| OpenAPI schema validation | `python manage.py spectacular --validate` to be run before final PR | Anji |
| CI PostgreSQL | Branch CI will run on PostgreSQL once PR is opened against `main` | Isha's CI pipeline |

---

## 8. Reused (Not Duplicated) Interfaces

| Interface | Owner | How Used |
|-----------|-------|---------|
| `User` model + `User.Role` enum | Deepak | Role checks in `IsIPCAdmin`; test fixtures |
| `SimpleJWT` auth backend | Deepak | `Authorization: Bearer` in all tests |
| `Company` + `RecruiterProfile` models | Charan | Recruiter verification reads/writes |
| `AlumniProfile` + `VerificationStatus` | Nayana | Alumni verification reads/writes |
| `drf-spectacular` OpenAPI schema | Deepak/Isha | Schema validation & Swagger UI |

---

## 9. Local Test Command

```powershell
cd nexus-career/backend
$env:PYTHONPATH = ".packages"
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = "local-test-key-s2-r1-at-least-32-bytes"
$env:DJANGO_DB_ENGINE = "django.db.backends.sqlite3"
python -m pytest tests/ apps/accounts/tests.py -v
# Expected: 36 passed
```
