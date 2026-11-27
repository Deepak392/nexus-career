# Alumni verification and referral workflows

This document describes the implemented Alumni and referral increment against the Nexus Career SRS.

## SRS traceability

| SRS requirement | Implemented behaviour |
|---|---|
| FR-ALM-01 | Alumni accounts receive a pending profile. Alumni submit a PDF graduation proof; IPC administrators review the private document and verify or reject the profile. |
| FR-ALM-02 | Alumni maintain department, degree programme, graduation year, current company, designation and industry. |
| FR-ALM-03 | Alumni can enable or disable referral availability. Only verified alumni with availability enabled are returned for referral discovery. |
| FR-ALM-04 | Alumni dashboard metrics are calculated from persisted referral requests and distinct student interactions. |
| FR-REF-01 | Students search verified alumni by company, designation and department, and can send a request to an available alumnus. |
| FR-REF-02 | A request requires an opportunity URL, PDF resume and a message. |
| FR-REF-03 | The assigned alumnus can accept, decline or request more information. The student can respond to an information request. |
| FR-REF-04 | Requests use Pending, Accepted, Referred and Declined statuses, with an append-only event history. |
| FR-NOT-02 / FR-NOT-04 | Referral events produce in-app notifications; each user can read and acknowledge only their own notifications. |

## Alumni verification lifecycle

1. Alumni complete their profile and submit graduation evidence as a PDF (maximum 5 MB).
2. The backend validates the file and stores it using a generated filename under the private media root.
3. The profile remains Pending until an IPC administrator reviews the evidence.
4. IPC administrators can download the proof using an authenticated endpoint and verify or reject the profile.
5. Rejection requires a reason. The reviewer, review time, verifier and verification time are recorded.
6. Only Verified profiles can appear in the student directory. Alumni must also enable referral availability to receive new requests.

Replacing the proof resets the profile to Pending and clears the previous verification decision. The proof is not exposed as a public media URL.

## Referral lifecycle

| Actor | Action | Result |
|---|---|---|
| Student | Submit a request | Creates a Pending request, history event and notification to the alumnus |
| Alumni | Accept | Moves Pending to Accepted and notifies the student |
| Alumni | Decline | Moves Pending to Declined and notifies the student |
| Alumni | Request information | Keeps Pending, records the request in history and notifies the student |
| Student | Respond | Keeps Pending, records the response and notifies the alumnus |
| Alumni | Mark referred | Moves Accepted to Referred and notifies the student |

An active request is unique for a student, alumnus and opportunity URL. Database constraints prevent duplicate active requests. Status changes are performed within transactions and history is retained.

## API contract

All routes are under `/api/v1` and require authentication unless stated otherwise.

| Method and route | Access | Purpose |
|---|---|---|
| `POST /alumni/graduation-proof/` | Alumni | Upload or replace graduation proof |
| `GET /alumni/ipc/pending-verification/` | IPC Admin | List pending profiles with submitted proof |
| `GET /alumni/ipc/{id}/proof/` | IPC Admin | Download a private graduation proof |
| `POST /alumni/ipc/{id}/verify/` | IPC Admin | Verify a profile |
| `POST /alumni/ipc/{id}/reject/` | IPC Admin | Reject a profile with a reason |
| `GET /alumni/search/` | Student | Search verified alumni |
| `GET /alumni/referral-requests/` | Student or Alumni | List the caller's own referral requests |
| `POST /alumni/referral-requests/` | Student | Submit a referral request |
| `GET /alumni/referral-requests/{id}/` | Request participants | Retrieve a request and its history |
| `POST /alumni/referral-requests/{id}/{action}/` | Assigned Alumni or Student requester | Perform an allowed referral action |
| `GET /alumni/referral-requests/{id}/resume/` | Request participants | Download the request's private PDF resume |
| `GET /alumni/metrics/` | Alumni | Retrieve engagement metrics |

Notification inbox routes are `GET /api/v1/notifications/` and `POST /api/v1/notifications/{id}/read/`.

## Access-control and file-handling notes

- Role checks are enforced by Django views; frontend route guards are only navigation controls.
- Graduation proof downloads are restricted to IPC administrators.
- Referral resume downloads are restricted to the student who submitted the request and the assigned alumnus.
- Referral lists and detail lookups are scoped to the authenticated participant. Other users receive no access to the record.
- Uploaded PDFs are validated by extension, MIME type, size and PDF signature and are stored below the private media root with generated names.
- Student directory results omit alumni email addresses and verification documents.
- Referral status changes, history records and notifications are persisted together in database transactions.

## Operational notes

- Apply the new alumni migrations with `python manage.py migrate`.
- Keep `PRIVATE_MEDIA_ROOT` outside the public/static frontend directory and ensure it is not served by the web server.
- The university/IPC should define its accepted graduation-evidence policy and retention period before production use. The current workflow validates PDF format but does not independently authenticate the issuing institution or perform automated document verification.
