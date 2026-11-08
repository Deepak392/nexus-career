# Sprint 2: Recruiter and Opportunity Approval Workflow

## Scope implemented in this increment

This increment adds the backend foundation for recruiter company management, opportunity submission, IPC company verification, IPC opportunity approval/rejection and workflow audit events.

## Recruiter onboarding decision

SRS assumption A-06 (direct recruiter registration versus IPC invitation) remains a stakeholder decision. This increment does not add public recruiter self-registration or let users assign themselves the RECRUITER role. Recruiter accounts must be provisioned by an authorized project administrator using the existing Django administration process until the university confirms the onboarding policy.

Company verification is a separate IPC-controlled step. Creating a company profile sets its status to PENDING. A recruiter can save draft opportunities, but cannot submit an opportunity until the associated company is VERIFIED.

Editing a company profile returns it to PENDING because company information must be reviewed again.

## Recruiter endpoints

All recruiter endpoints require an authenticated user with role RECRUITER.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/v1/recruiters/company/ | Retrieve own company profile |
| POST | /api/v1/recruiters/company/ | Create company profile and recruiter association |
| PATCH | /api/v1/recruiters/company/ | Update own company profile; resets verification |
| GET | /api/v1/recruiters/opportunities/ | List opportunities for own company |
| POST | /api/v1/recruiters/opportunities/ | Create a DRAFT opportunity |
| GET | /api/v1/recruiters/opportunities/{id}/ | Retrieve own-company opportunity |
| PATCH | /api/v1/recruiters/opportunities/{id}/ | Edit DRAFT or REJECTED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/submit/ | Submit DRAFT/REJECTED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/close/ | Close a PUBLISHED opportunity |
| POST | /api/v1/recruiters/opportunities/{id}/archive/ | Archive DRAFT, REJECTED or CLOSED opportunity |

## IPC endpoints

All IPC endpoints require an authenticated user with role IPC_ADMIN.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/v1/ipc/companies/pending/ | List companies awaiting verification |
| POST | /api/v1/ipc/companies/{id}/verify/ | Verify company |
| POST | /api/v1/ipc/companies/{id}/reject/ | Reject company; reason required |
| GET | /api/v1/ipc/opportunities/pending/ | List opportunities awaiting approval |
| POST | /api/v1/ipc/opportunities/{id}/approve/ | Approve and publish opportunity |
| POST | /api/v1/ipc/opportunities/{id}/reject/ | Reject opportunity; reason required |

## Eligibility criteria payload

eligibility_criteria is a JSON object. Supported keys in this increment:

- minimum_cgpa: number between 0 and 10
- graduation_years: array of positive integer years
- degree_programmes: array of non-empty strings
- departments: array of non-empty strings
- required_skills: array of non-empty strings

This is stored independently of required_skills so future eligibility evaluation can explain individual criteria.

## Workflow and audit

- Company records store verification status, reviewer, verification timestamp and rejection reason.
- Opportunity records store creator, approver, approval timestamp, publication timestamp and rejection reason.
- Each workflow transition creates a WorkflowAuditEvent with actor, action, object type/id, timestamp and optional details.
- Public opportunity discovery remains read-only and only returns published opportunities before their deadlines.

## Explicitly not included

- Recruiter account invitation/self-registration pending A-06.
- Automated university identity checks or email OTP.
- Full eligibility evaluation against student profiles.
- Application submission/review workflows.
- Email notifications.
