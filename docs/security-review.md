# Security review: resume upload and private-file access

Review date: 25 November 2026. Reviewer: Roopa (DevOps and security). Scope: resume and document upload, private-file download, authorization of student data, and production settings. Method: code reading of `main` plus the existing tests. Resume parsing does not exist in `main` yet, so it is covered as requirements only.

## Results

| Check | Result | Evidence |
|---|---|---|
| Upload validation (PDF only, 5 MB) | Pass (basic) | `validate_pdf_resume` checks size, `.pdf` extension, declared content type and the `%PDF-` signature |
| Validator used on every upload path | Pass | Student profile, referral request and graduation proof use it. Applications copy the student's stored resume. |
| Generated file names | Pass | Files are stored as `private/.../<random id>.pdf`, never under the client's name |
| No public URL for files | Pass | `MEDIA_ROOT` is `private_media`, and `urls.py` has no media route |
| API does not expose file paths | Pass | `resume` is write-only, responses show only `has_resume`, and a test covers it |
| A student cannot read another student's referral resume | Pass | `referral_queryset_for_user` filters by owner, other users get 404 |
| Alumni see only referrals addressed to them | Pass | Queryset filtered by `alumni_profile__user` |
| Recruiters and IPC admins cannot read referral resumes | Pass | Other roles get `PermissionDenied` |
| Graduation proof download | Pass | IPC admin only |
| Students see only their own applications | Pass | Queryset filtered by `student=request.user`, `IsStudent` permission |
| Recruiters see only their company's opportunities | Pass | Queryset filtered by company |
| Password reset does not log emails or tokens | Pass | Only the user id is logged |
| Secrets come from the environment | Pass | `SECRET_KEY`, `EMAIL_HOST_PASSWORD`, hosts and CORS read from env vars |
| Resume parsing | Not applicable | Not implemented yet (see requirements below) |

## Findings

| # | Severity | Finding | Acceptance criteria | Suggested owner |
|---|---|---|---|---|
| 1 | High | Vercel rejects request bodies above 4.5 MB by default, below the 5 MB resume limit | A resume at the maximum allowed size uploads successfully on the hosted site | Backend and hosting |
| 2 | Medium | Login and upload endpoints have no rate limit (only password reset does), although SRS 4.4 asks for rate limits | Repeated failed logins and rapid uploads return HTTP 429, with a test | Backend |
| 3 | Medium | No HTTPS or cookie settings (`SECURE_PROXY_SSL_HEADER`, secure cookies, HSTS) | With debug off, cookies are marked secure and HTTPS headers are sent | Backend |
| 4 | Medium | The email variables (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`) are missing from the hosted environment list. With debug off and no `EMAIL_HOST`, password reset emails fail silently. | A mail provider is chosen, the variables are set on the hosted site, and a reset email arrives | DevOps |
| 5 | Low | The PDF check relies on a header and client-declared type. No malware scan. | Optional: a PDF library confirms the structure once parsing exists | Backend |
| 6 | Low | Alumni keep access to a referral resume after declining it or losing verified status. Is this intended? | The team decides, and the behaviour is documented and tested | Product, then backend |
| 7 | To check | No endpoint was found that lets recruiters view applications or applicant resumes (BR-09, UC-04) | When built, a recruiter cannot reach another company's applicant, covered by tests | Backend |
| 8 | Low | Alumni views check roles inline, while other modules use permission classes | Alumni views use the shared permission classes | Backend |
| 9 | Low | Nothing records who downloaded a graduation proof or a resume (SRS NFR-SEC-09) | Each download writes an audit entry with the user, the file and the time (never the file contents) | Backend |

## Requirements for resume parsing (not built yet)

- Parse only files that passed `validate_pdf_resume`.
- Set a page limit and a time limit.
- Treat extracted text as untrusted: never render it as HTML and never write it to logs.
- Store only the text the eligibility feature needs.
- Pin the parsing library in `requirements/base.txt`, so Dependabot and `pip-audit` watch it.
- Return a clean error for unreadable files, with no stack trace.

## Tests

Authorization tests (to be added): another student gets 404 on a referral resume, an unauthenticated request gets 401, a recruiter gets 403.