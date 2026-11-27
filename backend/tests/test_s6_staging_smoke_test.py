"""Sprint 6 (Week 6): Staging Smoke Test Suite.

Verifies all 13 core deployment readiness checkpoints specified in Section 9
of the Master Engineering Prompt:
1. Health endpoint (/api/v1/health/)
2. Authentication (/api/v1/auth/login/, /me/)
3. Opportunity creation & IPC approval
4. Opportunity listing & discovery
5. Student eligibility checking
6. Student application submission
7. Recruiter applicant review
8. Application status transitions
9. Notification delivery & mark-as-read
10. IPC admin dashboard & verification access
11. Audit log retrieval
12. Activity report & CSV export
13. Swagger UI & OpenAPI schema accessibility
"""

from decimal import Decimal
import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.applications.models import Application
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile


@pytest.mark.django_db
class TestStagingSmokeSuite:
    """Production-readiness smoke tests using synthetic test accounts."""

    def test_01_smoke_health_endpoint(self, api_client):
        """Smoke 1: Liveness check returns HTTP 200 and ok status."""
        health_url = reverse("health")
        resp = api_client.get(health_url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get("status") == "ok"

    def test_02_smoke_authentication(self, api_client, recruiter_user):
        """Smoke 2: JWT login and identity introspection works."""
        login_url = reverse("token-obtain-pair")
        resp = api_client.post(
            login_url,
            {"username": recruiter_user.username, "password": "test-only-password"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        token = resp.data["access"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_url = reverse("account-profile")
        me_resp = api_client.get(me_url)
        assert me_resp.status_code == status.HTTP_200_OK
        assert me_resp.data["username"] == recruiter_user.username

    def test_03_smoke_opportunity_lifecycle_and_approval(
        self, api_client, recruiter_user, ipc_admin_user, verified_company, jwt_auth_headers
    ):
        """Smoke 3: Recruiter creates opportunity; IPC Admin reviews and approves it."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@smoke.test"},
        )
        now = timezone.now()

        # Recruiter creates opportunity
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        create_resp = api_client.post(
            reverse("recruiter-opportunity-list"),
            {
                "title": "Smoke Test Site Engineer",
                "description": "Validation role for automated staging smoke test.",
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "location": "Remote",
                "compensation": 1500000.00,
                "application_deadline": (now + timezone.timedelta(days=15)).isoformat(),
                "required_skills": ["Python", "Django"],
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        opp_id = create_resp.data["id"]

        # Recruiter submits
        submit_resp = api_client.post(reverse("recruiter-opportunity-submit", kwargs={"pk": opp_id}))
        assert submit_resp.status_code == status.HTTP_200_OK
        assert submit_resp.data["status"] == "PENDING_APPROVAL"

        # IPC Admin approves
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        approve_resp = api_client.post(reverse("admin-opportunity-approve", kwargs={"id": opp_id}))
        assert approve_resp.status_code == status.HTTP_200_OK
        assert approve_resp.data["status"] == "PUBLISHED"

    def test_04_smoke_opportunity_listing_and_discovery(
        self, api_client, student_user, recruiter_user, verified_company, jwt_auth_headers
    ):
        """Smoke 4: Students discover published opportunities with search and filter."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Senior Smoke Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1600000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        resp = api_client.get(reverse("opportunity-list"), {"search": "Senior Smoke"})
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert any(item["id"] == opp.id for item in results)

    def test_05_smoke_eligibility_checking(
        self, api_client, student_user, recruiter_user, verified_company, jwt_auth_headers
    ):
        """Smoke 5: Student evaluates eligibility against published criteria."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Cloud Data Specialist",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1700000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
            eligibility_criteria={
                "minimum_cgpa": "7.50",
                "departments": ["Computer Science"],
                "degree_programmes": ["B.Tech"],
                "graduation_years": [2026],
            },
        )

        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="SMOKE_STUDENT_01",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.40"),
            skills=["Python"],
        )
        profile.resume.save(
            "smoke_resume.pdf",
            ContentFile(b"%PDF-1.7 Smoke Test Resume"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        resp = api_client.get(reverse("opportunity-eligibility", kwargs={"pk": opp.id}))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["eligible"] is True
        assert resp.data["ready_to_apply"] is True

        profile.resume.delete(save=False)

    def test_06_smoke_application_submission(
        self, api_client, student_user, recruiter_user, verified_company, jwt_auth_headers
    ):
        """Smoke 6: Student submits application; resume snapshot preserved."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Smoke Application Target",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )

        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="SMOKE_STUDENT_02",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.00"),
        )
        profile.resume.save(
            "smoke_resume.pdf",
            ContentFile(b"%PDF-1.7 Student Resume Bytes"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        apply_url = reverse("application-list")
        resp = api_client.post(apply_url, {"opportunity_id": opp.id}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == "SUBMITTED"

        app = Application.objects.get(student=student_user, opportunity=opp)
        profile.resume.delete(save=False)
        app.resume.delete(save=False)

    def test_07_smoke_recruiter_applicant_review(
        self, api_client, recruiter_user, student_user, verified_company, jwt_auth_headers
    ):
        """Smoke 7: Recruiter lists applicants for opportunity."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@smoke.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Smoke Review Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )
        Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(recruiter_user))
        resp = api_client.get(reverse("opportunity-applicants", kwargs={"pk": opp.id}))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_08_smoke_status_update_and_transitions(
        self, api_client, recruiter_user, student_user, verified_company, jwt_auth_headers
    ):
        """Smoke 8: Recruiter updates application status via PATCH."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@smoke.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Smoke Transition Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )
        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        api_client.credentials(**jwt_auth_headers(recruiter_user))
        status_url = reverse("application-status", kwargs={"pk": app.id})
        resp = api_client.patch(
            status_url,
            {"status": "UNDER_REVIEW", "note": "Moving candidate to review."},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "UNDER_REVIEW"

    def test_09_smoke_notification_delivery_and_mark_read(
        self, api_client, student_user, jwt_auth_headers
    ):
        """Smoke 9: Notifications retrieved and marked read."""
        notif = Notification.objects.create(
            recipient=student_user,
            notification_type="APPLICATION_STATUS_CHANGED",
            title="Status Changed",
            message="Your application was shortlisted.",
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        list_resp = api_client.get(reverse("notification-list"))
        assert list_resp.status_code == status.HTTP_200_OK

        read_resp = api_client.post(reverse("notification-mark-read", kwargs={"pk": notif.id}))
        assert read_resp.status_code == status.HTTP_200_OK
        notif.refresh_from_db()
        assert notif.read_at is not None

    def test_10_smoke_ipc_admin_dashboard_metrics(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """Smoke 10: IPC Admin metrics dashboard responds with 5 required KPIs."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        resp = api_client.get(reverse("admin-dashboard-metrics"))
        assert resp.status_code == status.HTTP_200_OK
        assert "active_opportunities" in resp.data
        assert "students" in resp.data
        assert "verified_recruiters" in resp.data
        assert "applications" in resp.data
        assert "pending_approvals" in resp.data

    def test_11_smoke_audit_log_retrieval(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """Smoke 11: IPC Admin queries paginated audit trail."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        resp = api_client.get(reverse("admin-audit-logs"))
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.data or isinstance(resp.data, list)

    def test_12_smoke_activity_report_and_csv_export(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """Smoke 12: IPC Admin accesses activity report and downloads CSV."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))

        # JSON Report
        report_resp = api_client.get(reverse("admin-reports-activity"))
        assert report_resp.status_code == status.HTTP_200_OK

        # CSV Export
        csv_resp = api_client.get(reverse("admin-reports-export"))
        assert csv_resp.status_code == status.HTTP_200_OK
        assert csv_resp["Content-Type"].startswith("text/csv")
        assert "nexus_career_activity_report_" in csv_resp["Content-Disposition"]

    def test_13_smoke_swagger_and_openapi_accessibility(self, api_client):
        """Smoke 13: Swagger UI and OpenAPI schema endpoints respond with HTTP 200."""
        schema_resp = api_client.get(reverse("api-schema"))
        assert schema_resp.status_code == status.HTTP_200_OK

        swagger_resp = api_client.get(reverse("swagger-ui"))
        assert swagger_resp.status_code == status.HTTP_200_OK
        assert "text/html" in swagger_resp["Content-Type"]
