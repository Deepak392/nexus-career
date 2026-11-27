"""Tests verifying the resolution of DEF-S4-01, DEF-S4-02, DEF-S4-03, and DEF-S6-01."""

from decimal import Decimal
import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.accounts.models import User
from apps.applications.models import Application, ApplicationStatusHistory
from apps.applications.services import transition_application_status
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile


@pytest.fixture
def other_recruiter(user_factory):
    return user_factory(
        username="other_recruiter",
        role=User.Role.RECRUITER,
        email="other@othercorp.test",
    )


@pytest.fixture
def other_company():
    return Company.objects.create(
        name="Other Corp",
        website="https://othercorp.test",
        industry="Technology",
        verification_status=Company.VerificationStatus.VERIFIED,
    )


@pytest.mark.django_db
class TestDefectResolutionAndStatusTransitions:
    """Tests covering DEF-S4-01 (recruiter applicant list), DEF-S4-02 (status transition),

    and DEF-S4-03 (event wiring).
    """

    def test_recruiter_can_view_applicants_for_own_opportunity(
        self,
        api_client,
        recruiter_user,
        student_user,
        verified_company,
        jwt_auth_headers,
    ):
        """DEF-S4-01: Recruiter can list applicants for their company's opportunity."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@tech.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Senior Site Reliability Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1800000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(recruiter_user))

        # Test both endpoint forms:
        # 1. /api/v1/opportunities/{id}/applications/
        resp1 = api_client.get(reverse("opportunity-applicants", kwargs={"pk": opp.id}))
        assert resp1.status_code == status.HTTP_200_OK
        assert resp1.data["count"] == 1
        assert resp1.data["results"][0]["id"] == app.id
        assert resp1.data["results"][0]["student_username"] == student_user.username

        # 2. /api/v1/recruiters/opportunities/{id}/applications/
        resp2 = api_client.get(reverse("recruiter-opportunity-applications", kwargs={"pk": opp.id}))
        assert resp2.status_code == status.HTTP_200_OK
        results = resp2.data.get("results", resp2.data)
        assert len(results) == 1
        assert results[0]["id"] == app.id

    def test_cross_company_recruiter_cannot_view_other_company_applicants(
        self,
        api_client,
        recruiter_user,
        other_recruiter,
        student_user,
        verified_company,
        other_company,
        jwt_auth_headers,
    ):
        """DEF-S4-01 security guard: Recruiter B cannot see applicants for Recruiter A's opportunity."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiterA@tech.test"},
        )
        RecruiterProfile.objects.get_or_create(
            user=other_recruiter,
            defaults={"company": other_company, "work_email": "recruiterB@other.test"},
        )

        now = timezone.now()
        opp_a = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Company A Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )
        Application.objects.create(
            student=student_user,
            opportunity=opp_a,
            status=Application.Status.SUBMITTED,
        )

        # Recruiter B attempts to view applicants for Opportunity A
        api_client.credentials(**jwt_auth_headers(other_recruiter))

        resp1 = api_client.get(reverse("opportunity-applicants", kwargs={"pk": opp_a.id}))
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        resp2 = api_client.get(reverse("recruiter-opportunity-applications", kwargs={"pk": opp_a.id}))
        assert resp2.status_code == status.HTTP_404_NOT_FOUND

    def test_student_cannot_access_recruiter_applicant_review_endpoint(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """DEF-S4-01 role guard: Students receive 403 accessing applicant review."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Public Cloud Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        resp = api_client.get(reverse("opportunity-applicants", kwargs={"pk": opp.id}))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_recruiter_can_transition_application_status_via_api(
        self,
        api_client,
        recruiter_user,
        student_user,
        verified_company,
        jwt_auth_headers,
    ):
        """DEF-S4-02 & DEF-S4-03: Recruiter updates application status via PATCH /applications/{id}/status/."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@tech.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Distributed Systems Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=2000000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(recruiter_user))
        status_url = reverse("application-status", kwargs={"pk": app.id})

        # 1. Transition to UNDER_REVIEW
        resp1 = api_client.patch(
            status_url,
            {"status": "UNDER_REVIEW", "note": "Reviewing candidate portfolio"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_200_OK
        assert resp1.data["status"] == "UNDER_REVIEW"

        app.refresh_from_db()
        assert app.status == Application.Status.UNDER_REVIEW
        assert app.status_history.count() == 1
        assert app.status_history.first().status == "UNDER_REVIEW"

        # 2. Transition to SHORTLISTED
        resp2 = api_client.patch(
            status_url,
            {"status": "SHORTLISTED", "note": "Passed preliminary resume filter"},
            format="json",
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["status"] == "SHORTLISTED"

        app.refresh_from_db()
        assert app.status == Application.Status.SHORTLISTED
        assert app.status_history.count() == 2

        # 3. Verify notification delivered to student (DEF-S4-03)
        notif = Notification.objects.filter(
            recipient=student_user,
            notification_type="APPLICATION_STATUS_CHANGED",
        ).order_by("-created_at").first()
        assert notif is not None
        assert "SHORTLISTED" in notif.message

        # 4. Verify audit log entry
        logs = get_audit_logs()
        status_logs = [l for l in logs if l["action"] == "APPLICATION_STATUS_CHANGED"]
        assert len(status_logs) >= 2

    def test_invalid_status_transition_returns_400_bad_request(
        self,
        api_client,
        recruiter_user,
        student_user,
        verified_company,
        jwt_auth_headers,
    ):
        """DEF-S4-02: Invalid status transition is rejected with 400 Bad Request."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@tech.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Security Specialist",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1600000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(recruiter_user))
        status_url = reverse("application-status", kwargs={"pk": app.id})

        # Cannot jump directly from SUBMITTED to SELECTED
        resp = api_client.patch(
            status_url,
            {"status": "SELECTED", "note": "Direct jump"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_student_can_withdraw_own_application(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """DEF-S4-02: Student can withdraw their own application."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Database Developer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1400000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        status_url = reverse("application-status", kwargs={"pk": app.id})

        # Student withdraws
        resp = api_client.patch(
            status_url,
            {"status": "WITHDRAWN", "note": "Accepted another offer"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "WITHDRAWN"

        app.refresh_from_db()
        assert app.status == Application.Status.WITHDRAWN
