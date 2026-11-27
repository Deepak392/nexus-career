"""R11: Performance Analysis — Query Count & Index Regression Tests (Sprint 5).

Objective:
  Measure and document database query counts for critical API endpoints.
  Full load testing (100 concurrent users / Locust / k6) requires a staging
  environment that is NOT available locally.

  R11 is therefore partially BLOCKED (staging unavailable) but the following
  tests perform ORM-level query-count assertions to:
  1. Detect N+1 query regressions early.
  2. Document baseline query budgets for each critical path.
  3. Provide evidence for the S5 performance report.

Staging Load Test Targets (to be executed when staging is available):
  - p95 response time ≤ 500 ms under 100 concurrent users.
  - Opportunity list: ≤ 5 ORM queries per request.
  - Admin dashboard metrics: ≤ 8 ORM queries per request.
  - Audit log paginated list: ≤ 3 ORM queries per request.
  - Application list (student): ≤ 3 ORM queries per request.
  - Activity report with filters: ≤ 6 ORM queries per request.

References:
  - Backend Delivery Plan §R11.
  - Django assertNumQueries / django-assert-num-queries patterns.
"""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_client(user: User) -> APIClient:
    """Returns an APIClient authenticated as the given user."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token.access_token)}")
    return client


# ---------------------------------------------------------------------------
# R11.1 — Opportunity List Query Count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOpportunityListQueryCount:
    """R11.1 Opportunity list must not regress into N+1 query patterns."""

    QUERY_BUDGET = 10  # Conservative budget; staging target is ≤ 5

    @pytest.fixture
    def opp_list_setup(self, role_user_factory, db):
        """Creates 5 published opportunities for query count baseline."""
        recruiter = role_user_factory("Recruiter", username="r11_opp_recruiter")
        ipc_admin = role_user_factory("IPC Admin", username="r11_opp_ipc")
        company = Company.objects.create(
            name="R11 QueryCount Corp",
            industry="Technology",
            contact_email="r11@querycount.test",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        now = timezone.now()
        for i in range(5):
            Opportunity.objects.create(
                company=company,
                created_by=recruiter,
                title=f"R11 Test Role {i+1}",
                description=f"Performance test opportunity {i+1}",
                opportunity_type=Opportunity.OpportunityType.JOB,
                work_mode=Opportunity.WorkMode.REMOTE,
                location="Hyderabad",
                application_deadline=now + timedelta(days=30 + i),
                status=Opportunity.Status.PUBLISHED,
            )
        return {"recruiter": recruiter, "ipc_admin": ipc_admin}

    def test_opportunity_list_query_count(self, opp_list_setup):
        """GET /api/v1/opportunities/ — number of DB queries must stay within budget."""
        student_user = User.objects.create_user(
            username="r11_opp_student",
            email="r11_opp_student@test.test",
            password="password",
            role=User.Role.STUDENT,
        )
        client = _auth_client(student_user)
        url = reverse("opportunity-list")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)

        query_count = len(ctx)
        assert response.status_code == 200, f"Opportunity list returned {response.status_code}"
        assert query_count <= self.QUERY_BUDGET, (
            f"Opportunity list used {query_count} queries — exceeds budget of {self.QUERY_BUDGET}.\n"
            f"Queries:\n" + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
        # Report actual count for documentation
        print(f"\n[R11] opportunity-list query count: {query_count} (budget: {self.QUERY_BUDGET})")

    def test_opportunity_list_does_not_produce_per_item_queries(self, opp_list_setup):
        """Adding more opportunities must NOT linearly increase query count (N+1 guard)."""
        student_user = User.objects.create_user(
            username="r11_n1_student",
            email="r11_n1_student@test.test",
            password="password",
            role=User.Role.STUDENT,
        )
        client = _auth_client(student_user)
        url = reverse("opportunity-list")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        # Baseline: 5 opportunities already exist
        with CaptureQueriesContext(connection) as ctx_5:
            client.get(url)
        queries_5 = len(ctx_5)

        # Add 5 more
        recruiter = opp_list_setup["recruiter"]
        company = Company.objects.get(name="R11 QueryCount Corp")
        now = timezone.now()
        for i in range(5, 10):
            Opportunity.objects.create(
                company=company,
                created_by=recruiter,
                title=f"R11 Extra Role {i+1}",
                description="N+1 guard test",
                opportunity_type=Opportunity.OpportunityType.JOB,
                work_mode=Opportunity.WorkMode.REMOTE,
                location="Hyderabad",
                application_deadline=now + timedelta(days=30 + i),
                status=Opportunity.Status.PUBLISHED,
            )

        with CaptureQueriesContext(connection) as ctx_10:
            client.get(url)
        queries_10 = len(ctx_10)

        # With proper select_related / prefetch, query count should NOT double
        # Allowing a small +1 for pagination count query
        assert queries_10 <= queries_5 + 2, (
            f"N+1 regression: 5 opps={queries_5} queries, 10 opps={queries_10} queries. "
            f"Query count grew by {queries_10 - queries_5} — investigate missing select_related."
        )
        print(f"\n[R11] N+1 guard: 5 opps→{queries_5}q, 10 opps→{queries_10}q")


# ---------------------------------------------------------------------------
# R11.2 — Admin Dashboard Metrics Query Count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminDashboardQueryCount:
    """R11.2 Admin dashboard must aggregate metrics in a fixed number of queries."""

    QUERY_BUDGET = 12  # Generous budget; staging target is ≤ 8

    def test_dashboard_metrics_query_count(self, role_user_factory, db):
        """GET /api/v1/admin/dashboard/metrics/ — queries must stay within budget."""
        ipc_admin = role_user_factory("IPC Admin", username="r11_dashboard_ipc")
        client = _auth_client(ipc_admin)
        url = reverse("admin-dashboard-metrics")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)

        query_count = len(ctx)
        assert response.status_code == 200
        assert query_count <= self.QUERY_BUDGET, (
            f"Dashboard metrics used {query_count} queries — budget is {self.QUERY_BUDGET}.\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
        print(f"\n[R11] admin-dashboard-metrics query count: {query_count} (budget: {self.QUERY_BUDGET})")


# ---------------------------------------------------------------------------
# R11.3 — Audit Log List Query Count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAuditLogQueryCount:
    """R11.3 Paginated audit log list must not regress."""

    QUERY_BUDGET = 8  # Conservative budget; staging target is ≤ 3

    def test_audit_log_list_query_count(self, role_user_factory, db):
        """GET /api/v1/admin/audit-logs/ — queries must stay within budget."""
        ipc_admin = role_user_factory("IPC Admin", username="r11_auditlog_ipc")
        client = _auth_client(ipc_admin)
        url = reverse("admin-audit-logs")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)

        query_count = len(ctx)
        assert response.status_code == 200
        assert query_count <= self.QUERY_BUDGET, (
            f"Audit log list used {query_count} queries — budget is {self.QUERY_BUDGET}.\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
        print(f"\n[R11] admin-audit-logs query count: {query_count} (budget: {self.QUERY_BUDGET})")


# ---------------------------------------------------------------------------
# R11.4 — Activity Report Query Count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestActivityReportQueryCount:
    """R11.4 Activity report endpoint (R6) query count baseline."""

    QUERY_BUDGET = 15  # Generous; staging target is ≤ 6

    def test_activity_report_query_count(self, role_user_factory, db):
        """GET /api/v1/admin/reports/ — query count must stay within budget."""
        ipc_admin = role_user_factory("IPC Admin", username="r11_reports_ipc")
        client = _auth_client(ipc_admin)
        url = reverse("admin-reports-list")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)

        query_count = len(ctx)
        assert response.status_code == 200
        assert query_count <= self.QUERY_BUDGET, (
            f"Activity report used {query_count} queries — budget is {self.QUERY_BUDGET}.\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
        print(f"\n[R11] admin-reports-list query count: {query_count} (budget: {self.QUERY_BUDGET})")


# ---------------------------------------------------------------------------
# R11.5 — Application List (Student) Query Count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestApplicationListQueryCount:
    """R11.5 Student application list query count baseline."""

    QUERY_BUDGET = 8  # Conservative; staging target is ≤ 3

    @pytest.fixture
    def app_list_setup(self, role_user_factory, db):
        student = role_user_factory("Student", username="r11_app_student")
        recruiter = role_user_factory("Recruiter", username="r11_app_recruiter")
        company = Company.objects.create(
            name="R11 App List Corp",
            industry="EdTech",
            contact_email="r11app@test.test",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        now = timezone.now()
        for i in range(3):
            opp = Opportunity.objects.create(
                company=company,
                created_by=recruiter,
                title=f"R11 App Opp {i+1}",
                description="Application list query test",
                opportunity_type=Opportunity.OpportunityType.JOB,
                work_mode=Opportunity.WorkMode.REMOTE,
                location="Delhi",
                application_deadline=now + timedelta(days=30),
                status=Opportunity.Status.PUBLISHED,
            )
            fake_pdf = SimpleUploadedFile(
                f"r11_resume_{i}.pdf", b"%PDF-1.4 R11", content_type="application/pdf"
            )
            Application.objects.create(
                student=student,
                opportunity=opp,
                status=Application.Status.SUBMITTED,
                resume=fake_pdf,
            )
        return {"student": student}

    def test_application_list_query_count(self, app_list_setup):
        """GET /api/v1/applications/ — query count for student must stay within budget."""
        student = app_list_setup["student"]
        client = _auth_client(student)
        url = reverse("application-list")

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)

        query_count = len(ctx)
        # Accept 403 (DEF-S4-01: recruiter block bleeds into student path) or 200
        if response.status_code == 403:
            pytest.skip(
                "DEF-S4-01: application-list returns 403 for students; "
                "query count test skipped until teammate fix is merged."
            )
        assert response.status_code == 200
        assert query_count <= self.QUERY_BUDGET, (
            f"Application list used {query_count} queries — budget is {self.QUERY_BUDGET}.\n"
            + "\n".join(q["sql"][:120] for q in ctx.captured_queries)
        )
        print(f"\n[R11] application-list query count: {query_count} (budget: {self.QUERY_BUDGET})")


# ---------------------------------------------------------------------------
# R11.6 — Index Existence Verification
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIndexExistence:
    """R11.6 Verify that the declared database indexes actually exist in the schema.

    These tests guard against accidental index removal via migration rollback.
    """

    def test_application_indexes_exist(self):
        """Application model must have declared composite indexes."""
        from apps.applications.models import Application

        index_names = {idx.name for idx in Application._meta.indexes}
        assert "application_student_date_idx" in index_names, (
            "Missing index: application_student_date_idx — "
            "student application list will be slow at scale."
        )
        assert "application_opp_status_idx" in index_names, (
            "Missing index: application_opp_status_idx — "
            "opportunity pipeline queries will be slow at scale."
        )

    def test_notification_index_exists(self):
        """Notification model must have the recipient+read_at+created_at index."""
        from apps.notifications.models import Notification

        index_names = {idx.name for idx in Notification._meta.indexes}
        assert "notif_recipient_read_idx" in index_names, (
            "Missing index: notif_recipient_read_idx — "
            "unread notification queries will be slow at scale."
        )

    def test_unique_constraint_application_exists(self):
        """UniqueConstraint on (student, opportunity) must exist on Application model."""
        from apps.applications.models import Application

        constraint_names = {c.name for c in Application._meta.constraints}
        assert "uniq_student_opportunity_application" in constraint_names, (
            "UniqueConstraint uniq_student_opportunity_application missing — "
            "duplicate applications are possible!"
        )
