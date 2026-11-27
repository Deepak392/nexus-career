# Anji Sprint 2 R1: Authentication, Permission, and Verification Test Plan

**Status:** Prepared; executable API tests await integration contracts and endpoints.  
**Scope:** R1 recruiter/alumni verification and authentication/permission testing only.

This plan is based on the S2 master prompt. Expected status codes and policy outcomes must
be aligned with Deepak's shared authentication/permission behavior and the team's
resource-concealment conventions before assertions are finalized. No mock-only test will
be treated as proof of integration.

## Authentication cases

| ID | Request | Expected result | State assertion |
|---|---|---|---|
| A01 | No credentials to a protected verification operation | 401 under the agreed authentication scheme | No verification change and no success audit entry |
| A02 | Valid IPC administrator credentials | Authentication succeeds | Acting admin comes from the authenticated principal |
| A03 | Invalid credentials | Rejected by the existing authentication implementation | No protected operation is performed |
| A04 | Expired/invalid token, if the approved scheme uses tokens | Rejected | No protected operation is performed |
| A05 | Suspended account with otherwise valid credentials | Blocked according to Deepak's suspended-account contract | No verification change and no success audit entry |

## Role matrix

| ID | Acting role | Operation | Expected result |
|---|---|---|---|
| P01 | Student | Recruiter verification | Denied |
| P02 | Recruiter | Recruiter verification, including own company | Denied |
| P03 | Alumni | Recruiter or alumni verification | Denied |
| P04 | IPC Admin | Recruiter verification | Allowed only under the agreed IPC permission and resource rules |
| P05 | IPC Admin | Alumni verification | Allowed only under the agreed IPC permission and proof rules |
| P06 | System Admin | Either verification operation | Must match the explicitly agreed system-admin policy; do not assume IPC equivalence |

For every denied operation, assert both the agreed HTTP error and that the target record
and audit store remain unchanged. A forbidden request must not produce a success audit
entry.

## Recruiter/company verification cases

| ID | Scenario | Expected result |
|---|---|---|
| V01 | IPC admin submits a valid decision for an eligible company/recruiter | Success; agreed verification state and actor/timestamp are persisted |
| V02 | Non-IPC role attempts the decision | Denied; no state change |
| V03 | Recruiter attempts to verify their own company | Denied; no state change |
| V04 | Target ID does not exist | Agreed 404/resource-concealment response |
| V05 | Request contains an unsupported status or invalid payload | Agreed validation error; no state change |
| V06 | Request attempts a disallowed state transition | Agreed validation/conflict response; no state change |
| V11 | Successful decision | Audit service receives authenticated actor, target, action, and safe metadata |

The database-schema branch has `Company.VerificationStatus` values `PENDING`, `VERIFIED`,
and `REJECTED`, plus `verified_by` and `verified_at`. These are on a separate branch and
must be integrated/reviewed before these become executable tests. The team still needs to
confirm allowed transitions, reason requirements, re-verification, and whether status
belongs to the company, recruiter, or both.

## Alumni/object-access cases

| ID | Scenario | Expected result |
|---|---|---|
| V07 | IPC admin verifies an alumnus with accessible, valid proof | Success under the agreed alumni contract |
| V08 | Student/recruiter/alumni attempts alumni verification | Denied; no state change |
| V09 | Proof is missing or inaccessible | Decision blocked according to policy; no state change |
| O01 | User changes a target ID to address another user's protected data | Denied or concealed according to shared policy |
| O02 | Unauthorized user requests graduation proof | Denied; proof URL/content is not exposed |
| O03 | IPC admin reaches an unrelated resource through an unauthorized operation | Denied |

Alumni profile and proof submission/access interfaces are not present in the inspected
checkout or the inspected database-schema branch. These cases cannot be executed until
Nayana's real interface is integrated.

## Test implementation requirements once dependencies are available

- Reuse `api_client` and role fixtures from `backend/tests/conftest.py`, adapting them to
  the production `accounts.User` model and the approved authentication method.
- Use real endpoint routes, models, permission classes, and audit service. Mock only
  boundaries that are unavailable in a focused unit test; retain integration coverage
  against real interfaces.
- Assert response, database state, and audit effects for both allowed and denied writes.
- Add endpoint tests to the existing pytest suite and keep them under the backend's
  configured `tests/` discovery path.
- Run the full PostgreSQL-backed suite and schema validation after implementation.

