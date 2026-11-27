# Anji Sprint 2 R1: API Documentation Draft

**Status:** Contract draft only; no verification endpoint is implemented or registered.  
**Purpose:** Capture the information needed to document the real endpoints in generated
OpenAPI after the team agrees on contracts.

## Recruiter/company verification

The delivery plan proposes:

```text
POST /api/v1/admin/recruiters/{id}/verify/
```

This path is not registered. The path, target entity, method, permission, transition
rules, and payload must be confirmed with Deepak and Charan before implementation.

### Proposed documentation fields (pending agreement)

- **Purpose:** IPC-controlled review decision for an eligible recruiter/company record.
- **Authentication:** Existing approved authentication implementation (TBD).
- **Permission:** Existing shared IPC verification permission (TBD).
- **Path parameter:** `id` — identifier of the agreed review target (TBD).
- **Request body:** The S2 prompt gives an illustrative `status` and `reason` example; the
  accepted values and whether a reason is required remain TBD.
- **Success response:** Agreed schema containing only the fields approved for clients (TBD).
- **Errors:** Unauthorized, forbidden, missing/concealed target, invalid decision, and
  invalid transition responses according to shared API conventions (TBD).
- **Audit:** Successful decisions use Deepak's audit service; response must not expose
  private evidence or sensitive audit metadata.

The separate `origin/feature/database-schema` branch currently models company statuses
`PENDING`, `VERIFIED`, and `REJECTED`, and fields `verified_by`/`verified_at`. This model
branch is not integrated into the current feature branch, and it does not by itself define
the API contract or authorization rules.

## Alumni verification

No alumni verification path is specified in the ownership section of the master prompt.
Do not register or document a guessed path. Agree with Nayana and Deepak on the target
model, protected proof-access interface, request/response schema, status ownership, and
permission before documenting an endpoint.

## OpenAPI upkeep checklist

When the contracts and implementation are available:

1. Register actual routes under `/api/v1/` with trailing slashes.
2. Use the real serializers and shared permission/authentication classes.
3. Add `drf-spectacular` metadata for auth, permissions, parameters, request/response
   schemas, validation outcomes, and safe synthetic examples.
4. Include only implemented routes in the generated schema.
5. Add schema/API tests and run `python manage.py spectacular --validate`.

