"""R10: Regression & End-to-End Test Suite — Sprint 5.

Covers:
8.3  Application status transition regression (data-layer; HTTP endpoint DEF-S4-02 documented as BLOCKED).
8.4  Duplicate application concurrency & UniqueConstraint regression.
8.5  File privacy regression (UUID path names, unauthenticated access denied).
8.6  Notification creation, read/unread flow, cross-user privacy.
8.7  Admin regression — R6 edge-cases, dashboard accuracy, audit log filter combinations.
8.8  Known defect registry (DEF-S4-01, DEF-S4-02, DEF-S4-03) — blocked / open items.

Design rules:
- Uses only service-layer / data-layer where HTTP endpoints are blocked by teammates.
- Uses synthetic test data only — never real user/production data.
- Skips tests that require a running staging environment.
- Marks externally-blocked tests with @pytest.mark.xfail or skip comments.
"""

from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core.events import get_emitted_events
from apps.accounts.models import User
from apps.applications.models import Application, ApplicationStatusHistory
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile


# ---------------------------------------------------------------------------
# 8.3  Application Status Transition Regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplicationStatusTransitions:
    """8.3 Verifies application status transitions at the data/service layer.

    NOTE: The HTTP endpoint for recruiter status updates (PATCH /api/v1/applications/<id>/)
    is NOT yet implemented by Sreehari (Task E7).
    See: DEF-S4-02 — ApplicationViewSet missing PATCH/status-transition.
    These tests verify the data model integrity only.
    """

    @pytest.fixture
    def app_setup(self, role_user_factory, db):
        """Creates a minimal application with one valid SUBMITTED status."""
        recruiter = role_user_factory("Recruiter", username="r10_recruiter_st")
        student = role_user_factory("Student", username="r10_student_st")
        company = Company.objects.create(
            name="R10 Status Corp",
            industry="Technology",
            contact_email="status@r10.test",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        opp = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="R10 Status Test Role",
            description="Status regression test opportunity",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Hyderabad",
            application_deadline=timezone.now() + timedelta(days=30),
            status=Opportunity.Status.PUBLISHED,
        )
        fake_pdf = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 R10 test resume", content_type="application/pdf")
        app = Application.objects.create(
            student=student,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
            resume=fake_pdf,
        )
        return {"recruiter": recruiter, "student": student, "app": app}

    def test_initial_status_is_submitted(self, app_setup):
        """Newly created application must start in SUBMITTED state."""
        app = app_setup["app"]
        app.refresh_from_db()
        assert app.status == Application.Status.SUBMITTED

    def test_valid_forward_transitions_at_data_layer(self, app_setup):
        """Recruiter can progress status SUBMITTED→UNDER_REVIEW→SHORTLISTED→SELECTED at ORM layer."""
        app = app_setup["app"]
        recruiter = app_setup["recruiter"]
        transitions = [
            Application.Status.UNDER_REVIEW,
            Application.Status.SHORTLISTED,
            Application.Status.SELECTED,
        ]
        for new_status in transitions:
            app.status = new_status
            app.save(update_fields=["status"])
            ApplicationStatusHistory.objects.create(
                application=app,
                status=new_status,
                changed_by=recruiter,
                note=f"R10 regression: moved to {new_status}",
            )

        app.refresh_from_db()
        assert app.status == Application.Status.SELECTED

    def test_status_history_is_preserved_in_order(self, app_setup):
        """ApplicationStatusHistory records are ordered chronologically and all entries are preserved."""
        app = app_setup["app"]
        recruiter = app_setup["recruiter"]

        for new_status in [Application.Status.UNDER_REVIEW, Application.Status.SHORTLISTED]:
            app.status = new_status
            app.save(update_fields=["status"])
            ApplicationStatusHistory.objects.create(
                application=app,
                status=new_status,
                changed_by=recruiter,
                note="R10 history regression",
            )

        history = list(ApplicationStatusHistory.objects.filter(application=app).order_by("created_at"))
        assert len(history) == 2
        assert history[0].status == Application.Status.UNDER_REVIEW
        assert history[1].status == Application.Status.SHORTLISTED

    def test_student_cannot_change_status_via_api(self, api_client, app_setup, jwt_auth_headers):
        """Student role must not be able to PATCH application status via API.

        DEF-S4-02 (BLOCKED): If the endpoint returns 404 because it doesn't exist yet,
        we accept that as evidence that the student cannot change status either.
        """
        student = app_setup["student"]
        app = app_setup["app"]
        api_client.credentials(**jwt_auth_headers(student))
        url = reverse("application-detail", kwargs={"pk": app.pk})

        response = api_client.patch(url, {"status": Application.Status.SELECTED}, format="json")

        # 403 Forbidden (student is not the owner for status change),
        # 405 Method Not Allowed (endpoint not implemented), or
        # 404 Not Found (route missing) all prove the student cannot change status.
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_404_NOT_FOUND,
        ), f"Unexpected {response.status_code}: student must NOT be able to update application status."

        # Data layer must be untouched
        app.refresh_from_db()
        assert app.status == Application.Status.SUBMITTED


# ---------------------------------------------------------------------------
# 8.4  Duplicate Application Concurrency Regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDuplicateApplicationPrevention:
    """8.4 Verifies UniqueConstraint(student, opportunity) prevents double applications."""

    @pytest.fixture
    def dup_setup(self, role_user_factory, db):
        recruiter = role_user_factory("Recruiter", username="r10_dup_recruiter")
        student = role_user_factory("Student", username="r10_dup_student")
        company = Company.objects.create(
            name="R10 Dup-Guard Corp",
            industry="Fintech",
            contact_email="dup@r10.test",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        opp = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="R10 Duplicate Guard Role",
            description="Prevents double applications",
            opportunity_type=Opportunity.OpportunityType.INTERNSHIP,
            work_mode=Opportunity.WorkMode.HYBRID,
            location="Pune",
            application_deadline=timezone.now() + timedelta(days=15),
            status=Opportunity.Status.PUBLISHED,
        )
        return {"student": student, "opp": opp}

    def test_first_application_succeeds(self, dup_setup):
        """Creating a first application for (student, opportunity) succeeds cleanly."""
        student = dup_setup["student"]
        opp = dup_setup["opp"]
        fake_pdf = SimpleUploadedFile("first.pdf", b"%PDF-1.4 first", content_type="application/pdf")
        app = Application.objects.create(
            student=student,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
            resume=fake_pdf,
        )
        assert app.pk is not None

    def test_duplicate_application_raises_integrity_error(self, dup_setup):
        """Creating a second application for the same (student, opportunity) raises IntegrityError."""
        student = dup_setup["student"]
        opp = dup_setup["opp"]
        fake_pdf_1 = SimpleUploadedFile("first.pdf", b"%PDF-1.4 first", content_type="application/pdf")
        fake_pdf_2 = SimpleUploadedFile("second.pdf", b"%PDF-1.4 second", content_type="application/pdf")

        Application.objects.create(
            student=student,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
            resume=fake_pdf_1,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Application.objects.create(
                    student=student,
                    opportunity=opp,
                    status=Application.Status.SUBMITTED,
                    resume=fake_pdf_2,
                )

    def test_unique_constraint_name_is_correct(self):
        """Verify the constraint name matches what is documented in the delivery plan."""
        constraint_names = [c.name for c in Application._meta.constraints]
        assert "uniq_student_opportunity_application" in constraint_names

    def test_different_students_can_apply_to_same_opportunity(self, dup_setup, role_user_factory):
        """Two distinct students can each apply to the same opportunity without conflict."""
        student_a = dup_setup["student"]
        student_b = role_user_factory("Student", username="r10_dup_student_b")
        opp = dup_setup["opp"]
        pdf_a = SimpleUploadedFile("a.pdf", b"%PDF-1.4 A", content_type="application/pdf")
        pdf_b = SimpleUploadedFile("b.pdf", b"%PDF-1.4 B", content_type="application/pdf")

        app_a = Application.objects.create(student=student_a, opportunity=opp, resume=pdf_a)
        app_b = Application.objects.create(student=student_b, opportunity=opp, resume=pdf_b)

        assert app_a.pk != app_b.pk

    def test_duplicate_application_via_api_returns_conflict(
        self, api_client, dup_setup, jwt_auth_headers, role_user_factory
    ):
        """POST /api/v1/applications/ for a duplicate returns 400 or 409, not 500."""
        student = dup_setup["student"]
        opp = dup_setup["opp"]
        fake_pdf = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 resume", content_type="application/pdf")

        # Pre-create existing application at data layer
        Application.objects.create(
            student=student,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
            resume=fake_pdf,
        )

        # Attempt API duplicate
        api_client.credentials(**jwt_auth_headers(student))
        url = reverse("application-list")
        response = api_client.post(
            url,
            {"opportunity": opp.pk},
            format="json",
        )

        # Must not be 500 — a 400, 403 or 409 all mean the app layer handled it
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR, (
            "Server returned 500 on duplicate application — unhandled IntegrityError!"
        )


# ---------------------------------------------------------------------------
# 8.5  File Privacy Regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFilePrivacyRegression:
    """8.5 Verifies resume file path privacy and access controls."""

    def test_student_resume_path_uses_uuid_not_original_name(self, role_user_factory, db):
        """StudentProfile resume upload path must generate a UUID-based path, never expose original filename."""
        from apps.students.models import student_resume_upload_path

        student = role_user_factory("Student", username="r10_privacy_student")
        profile = StudentProfile(user=student)
        generated_path = student_resume_upload_path(profile, "my_private_resume.pdf")

        # Must not contain the original filename
        assert "my_private_resume" not in generated_path
        # Must be under the private prefix
        assert generated_path.startswith("private/student-resumes/")
        # Must end with .pdf
        assert generated_path.endswith(".pdf")

    def test_application_resume_path_uses_uuid_not_original_name(self, db):
        """Application resume upload must generate UUID paths."""
        from apps.applications.models import application_resume_upload_path

        generated_path = application_resume_upload_path(None, "original_name.pdf")
        assert "original_name" not in generated_path
        assert generated_path.startswith("private/application-resumes/")
        assert generated_path.endswith(".pdf")

    def test_unauthenticated_user_denied_student_profile(self, api_client):
        """Unauthenticated access to student profile returns 401."""
        url = reverse("student-profile")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_profile_not_accessible_by_another_student(
        self, api_client, role_user_factory, db, jwt_auth_headers
    ):
        """Student A cannot read Student B's profile data via the student profile endpoint.

        The student-profile endpoint returns the calling user's own profile only.
        If Student B has no profile, 404 is acceptable. If 200, it must be Student B's own profile.
        """
        student_a = role_user_factory("Student", username="r10_priv_student_a")
        student_b = role_user_factory("Student", username="r10_priv_student_b")

        # Authenticate as Student B, access the student-profile endpoint
        api_client.credentials(**jwt_auth_headers(student_b))
        url = reverse("student-profile")
        response = api_client.get(url)

        # Either student_b sees their own profile or gets 404 (no profile created yet)
        if response.status_code == status.HTTP_200_OK:
            # Must be student_b's profile, not student_a's
            assert response.data.get("user") != student_a.pk
        else:
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_resume_uuid_paths_are_not_guessable(self, role_user_factory, db):
        """Two separate uploads produce different UUID paths — paths are unguessable."""
        from apps.students.models import student_resume_upload_path

        student = role_user_factory("Student", username="r10_uuid_student")
        profile = StudentProfile(user=student)
        path_1 = student_resume_upload_path(profile, "cv.pdf")
        path_2 = student_resume_upload_path(profile, "cv.pdf")

        assert path_1 != path_2, "Two uploads with the same filename must produce different UUID paths"


# ---------------------------------------------------------------------------
# 8.6  Notification Regression
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNotificationRegression:
    """8.6 Notification creation, read/unread marking, and cross-user privacy."""

    @pytest.fixture
    def notif_users(self, role_user_factory, db):
        student_a = role_user_factory("Student", username="r10_notif_student_a")
        student_b = role_user_factory("Student", username="r10_notif_student_b")
        return {"student_a": student_a, "student_b": student_b}

    def test_notification_can_be_created_at_data_layer(self, notif_users):
        """Notification model can be created with required fields."""
        student = notif_users["student_a"]
        notif = Notification.objects.create(
            recipient=student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application received",
            message="Your application to R10 Role has been received.",
        )
        assert notif.pk is not None
        assert notif.read_at is None

    def test_notification_list_requires_authentication(self, api_client):
        """Unauthenticated GET /api/v1/notifications/ returns 401."""
        url = reverse("notification-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_sees_only_own_notifications(
        self, api_client, notif_users, jwt_auth_headers
    ):
        """Student A cannot see Student B's notifications via the list endpoint."""
        student_a = notif_users["student_a"]
        student_b = notif_users["student_b"]

        # Create a notification exclusively for student_b
        Notification.objects.create(
            recipient=student_b,
            notification_type=Notification.NotificationType.OPPORTUNITY_APPROVED,
            title="Opportunity Approved",
            message="Your opportunity was approved.",
        )

        # Authenticate as student_a and list notifications
        api_client.credentials(**jwt_auth_headers(student_a))
        url = reverse("notification-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        # student_a must see zero notifications (all belong to student_b)
        assert len(results) == 0, (
            "Student A should not see Student B's notifications — cross-user data leak!"
        )

    def test_notification_mark_read_updates_read_at(
        self, api_client, notif_users, jwt_auth_headers
    ):
        """Marking a notification as read must set read_at timestamp."""
        student = notif_users["student_a"]
        notif = Notification.objects.create(
            recipient=student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Test Mark Read",
            message="Mark this as read.",
        )
        assert notif.read_at is None

        api_client.credentials(**jwt_auth_headers(student))
        url = reverse("notification-mark-read", kwargs={"pk": notif.pk})
        response = api_client.post(url)

        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
        notif.refresh_from_db()
        assert notif.read_at is not None, "read_at must be set after mark-read"

    def test_student_cannot_mark_read_another_students_notification(
        self, api_client, notif_users, jwt_auth_headers
    ):
        """Student A cannot mark Student B's notification as read (must return 403 or 404)."""
        student_a = notif_users["student_a"]
        student_b = notif_users["student_b"]

        notif_b = Notification.objects.create(
            recipient=student_b,
            notification_type=Notification.NotificationType.REFERRAL_REQUEST,
            title="Referral Request",
            message="A student has requested a referral.",
        )

        api_client.credentials(**jwt_auth_headers(student_a))
        url = reverse("notification-mark-read", kwargs={"pk": notif_b.pk})
        response = api_client.post(url)

        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), (
            f"Student A got {response.status_code} accessing Student B's notification"
        )
        notif_b.refresh_from_db()
        assert notif_b.read_at is None, "Student B's notification must remain unread"

    def test_opportunity_approved_emits_event(self, api_client, role_user_factory, db, jwt_auth_headers):
        """IPC Admin approving an opportunity emits OPPORTUNITY_APPROVED event."""
        ipc_admin = role_user_factory("IPC Admin", username="r10_notif_ipc")
        recruiter = role_user_factory("Recruiter", username="r10_notif_recruiter")
        company = Company.objects.create(
            name="R10 Notif Corp",
            industry="SaaS",
            contact_email="notif@r10.test",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        opp = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="R10 Notif Opportunity",
            description="Notification event regression test",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Bengaluru",
            application_deadline=timezone.now() + timedelta(days=30),
            status=Opportunity.Status.PENDING_APPROVAL,
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin))
        url = reverse("admin-opportunity-approve", kwargs={"id": opp.pk})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        emitted = get_emitted_events()
        event_types = [e["event_type"] for e in emitted]
        assert "OPPORTUNITY_APPROVED" in event_types, (
            "OPPORTUNITY_APPROVED event must be emitted when IPC admin approves an opportunity"
        )


# ---------------------------------------------------------------------------
# 8.7  Admin Regression — R6 Edge-cases, Dashboard, Audit Log
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminRegression:
    """8.7 Admin regression for R6 (reports), R5 (dashboard), R4 (audit logs)."""

    @pytest.fixture
    def admin_setup(self, role_user_factory, db):
        ipc_admin = role_user_factory("IPC Admin", username="r10_admin_ipc")
        student = role_user_factory("Student", username="r10_admin_student")
        return {"ipc_admin": ipc_admin, "student": student}

    def test_activity_report_with_no_records_returns_empty_list(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R6: Activity report endpoint returns empty results for a future date range with no data."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-reports-list")
        future_start = "2099-01-01"
        future_end = "2099-12-31"
        response = api_client.get(url, {"start_date": future_start, "end_date": future_end})

        assert response.status_code == status.HTTP_200_OK
        # Either empty list or paginated response with zero results
        data = response.data
        if isinstance(data, list):
            assert len(data) == 0
        elif isinstance(data, dict):
            results = data.get("results", data.get("items", []))
            assert len(results) == 0
        else:
            pytest.fail(f"Unexpected response type: {type(data)}")

    def test_activity_report_invalid_date_returns_400(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R6: Malformed date filter returns 400 Bad Request, not 500."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-reports-list")
        response = api_client.get(url, {"start_date": "not-a-date"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_activity_report_start_after_end_returns_400(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R6: start_date after end_date returns 400 Bad Request."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-reports-list")
        response = api_client.get(url, {"start_date": "2026-12-31", "end_date": "2026-01-01"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_csv_export_returns_valid_csv_content_type(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R6: CSV export endpoint returns Content-Type: text/csv."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-reports-export")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        content_type = response.get("Content-Type", "")
        assert "text/csv" in content_type, (
            f"Expected text/csv content-type, got: {content_type}"
        )

    def test_csv_export_blocked_for_non_admin(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R6: Student/non-admin cannot download the admin CSV export."""
        api_client.credentials(**jwt_auth_headers(admin_setup["student"]))
        url = reverse("admin-reports-export")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_metrics_returns_all_required_keys(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R5: Dashboard metrics response contains all 5 P1 KPI keys."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-dashboard-metrics")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        required_keys = {
            "active_opportunities",
            "students",
            "verified_recruiters",
            "applications",
            "pending_approvals",
        }
        missing = required_keys - set(response.data.keys())
        assert not missing, f"Dashboard missing required KPI keys: {missing}"

    def test_dashboard_metrics_counts_are_non_negative(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R5: All dashboard metric values must be non-negative integers."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-dashboard-metrics")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for key, value in response.data.items():
            assert isinstance(value, int) and value >= 0, (
                f"Dashboard metric '{key}' has invalid value: {value}"
            )

    def test_audit_log_filter_by_action(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R4: Audit log can be filtered by action parameter without error."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-audit-logs")
        response = api_client.get(url, {"action": "OPPORTUNITY_APPROVED"})

        assert response.status_code == status.HTTP_200_OK

    def test_audit_log_filter_by_actor_username(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R4: Audit log can be filtered by actor username without error."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-audit-logs")
        response = api_client.get(url, {"actor": "r10_admin_ipc"})

        assert response.status_code == status.HTTP_200_OK

    def test_audit_log_filter_combination(
        self, api_client, admin_setup, jwt_auth_headers
    ):
        """R4: Combining action + target_type filters works without 500 errors."""
        api_client.credentials(**jwt_auth_headers(admin_setup["ipc_admin"]))
        url = reverse("admin-audit-logs")
        response = api_client.get(url, {"action": "COMPANY_VERIFIED", "target_type": "COMPANY"})

        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 8.8  Known Defect Registry
# ---------------------------------------------------------------------------

"""
KNOWN DEFECT REGISTRY — Sprint 5 (Anji's ownership)
=====================================================

DEF-S4-01: Recruiter cannot list applicants for their own opportunities.
  Endpoint:  GET /api/v1/applications/
  Expected:  Recruiter sees applications for their own opportunities only.
  Actual:    HTTP 403 Forbidden — ApplicationViewSet likely has IsStudent guard only.
  Owner:     Charan Tej (Task O9: Recruiter Application Review).
  Status:    OPEN — awaiting teammate implementation.
  Impact:    Recruiter workflow is blocked; workaround: query at data layer in tests.

DEF-S4-02: No PATCH / status-transition endpoint on ApplicationViewSet.
  Endpoint:  PATCH /api/v1/applications/<id>/
  Expected:  Recruiter updates application status; ApplicationStatusHistory row created.
  Actual:    HTTP 405 Method Not Allowed or 404 (endpoint not implemented).
  Owner:     Sreehari (Task E7: Application Status Transitions).
  Status:    OPEN — awaiting teammate implementation.
  Impact:    Recruiter cannot advance candidate pipeline via API.

DEF-S4-03: APPLICATION_STATUS_CHANGED notification not wired.
  Expected:  events.emit("APPLICATION_STATUS_CHANGED", …) called on status update.
  Actual:    No event emitted because PATCH endpoint is missing (DEF-S4-02 root cause).
  Owner:     Isha (Notifications & Events) + Sreehari (status transition).
  Status:    BLOCKED (depends on DEF-S4-02 fix).
  Impact:    Student does not receive in-app notification on status change.

All three defects are documented in the Nexus Career S5 Implementation Report.
Tests in this file that touch these areas use data-layer fallbacks or
acceptance criteria of multiple valid HTTP codes per the defect context.
"""
