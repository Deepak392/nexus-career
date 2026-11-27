# Student eligibility, applications and notifications

This implementation covers the student eligibility and application workflows in the Nexus Career SRS, including FR-STU-04/05, FR-ELIG-01 through FR-ELIG-06, FR-APP-01, FR-APP-04, FR-APP-07 and FR-NOT-01.

## Student profile and resume

Students manage academic information at /profile. A profile stores department, degree programme, expected graduation year, optional CGPA, skills and preferences.

Resume uploads accept PDF files up to 5 MB. The backend validates the extension, declared MIME type and PDF signature. Uploads receive generated storage names and are saved beneath the private media root. The application does not expose a public media URL. The profile API returns only a has_resume indicator; the raw resume file is never returned in the profile response.

Replacing or removing a profile resume does not change the private resume copy already attached to an application.

## Eligibility API

GET /api/v1/opportunities/{id}/eligibility/

Authentication: required. Role: STUDENT.

The API compares the authenticated student's profile with the published opportunity's configured criteria:

- minimum_cgpa: the student's CGPA must be greater than or equal to the configured minimum.
- graduation_years: the student's expected graduation year must be one of the allowed years.
- degree_programmes: the student's degree programme must match one of the configured values, case-insensitively.
- departments: the student's department must match one of the configured values, case-insensitively.
- required_skills: all skills in Opportunity.required_skills and eligibility_criteria.required_skills must be present in the student's profile, case-insensitively.

Each criterion returns MET, NOT_MET or MISSING. Overall status is:

- ELIGIBLE: all configured criteria are satisfied.
- INELIGIBLE: at least one configured criterion is not satisfied.
- INCOMPLETE_PROFILE: required information is missing or the student has no profile.

The endpoint returns reasons and missing fields. It does not calculate or invent a candidate match score. In this increment, configured criteria are treated as mandatory for application eligibility; configurable IPC exceptions are not implemented.

The response includes ready_to_apply. Platform applications require eligibility and a saved PDF resume. External opportunities require eligibility, but do not require a resume to be uploaded to Nexus Career because the student completes that application on the recruiter's website.

## Platform application API

POST /api/v1/applications/

Authentication: required. Role: STUDENT.

Request body:

~~~json
{
  "opportunity_id": 123
}
~~~

The server rechecks that the opportunity is published and before its deadline, uses the platform application method, the student's profile meets all configured criteria and a valid PDF resume is available. The server copies the submitted resume into private application storage using a generated filename, preserving the version used at submission time.

A successful request returns 201 Created and creates an application in SUBMITTED status with an initial status-history event. A unique database constraint prevents duplicate applications for the same student and opportunity; duplicates return 409 Conflict.

Students can view their own paginated records at GET /api/v1/applications/. The endpoint is scoped to the authenticated student. GET /api/v1/applications/{id}/ returns one of that student's own records.

## In-app notifications

A successful application submission creates an APPLICATION_SUBMITTED notification in the same database transaction as the application and initial status-history record.

- GET /api/v1/notifications/ returns notifications for the authenticated user only.
- POST /api/v1/notifications/{id}/read/ marks one of the authenticated user's notifications as read.

The notification inbox is available at /notifications.

## External applications

For an EXTERNAL opportunity, the opportunity detail response carries the exact recruiter-provided external_application_url. Once the student meets the configured eligibility criteria, the frontend opens that URL in a new tab with rel="noopener noreferrer".

The student completes the submission on the recruiter's website. Nexus Career does not claim that the external application was submitted or include it in the platform application tracker because direct external-portal integration is out of scope for the MVP.

## Scope note

Student submission, eligibility, duplicate prevention, the initial status/history, in-app submission notification and student tracking are implemented in this increment. Recruiter/IPC review actions and subsequent recruitment status transitions remain a separate workflow increment. The application model includes the status vocabulary and status history needed for that work.
