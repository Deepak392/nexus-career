import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile


@pytest.mark.django_db
class TestAdminDashboardMetrics:
    """Tests the foundational IPC Admin Dashboard Metrics API (R5)."""

    def test_ipc_admin_can_access_dashboard_metrics(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """M01: Authorized IPC admin successfully retrieves dashboard metrics."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-dashboard-metrics")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        for required_key in [
            "active_opportunities",
            "students",
            "verified_recruiters",
            "applications",
            "pending_approvals",
        ]:
            assert required_key in data
            assert isinstance(data[required_key], int)

    def test_system_admin_can_access_dashboard_metrics(
        self, api_client, system_admin_user, jwt_auth_headers
    ):
        """M02: System administrator has access to the metrics dashboard."""
        api_client.credentials(**jwt_auth_headers(system_admin_user))
        url = reverse("admin-dashboard-metrics")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthorized_roles_are_forbidden(
        self,
        api_client,
        student_user,
        recruiter_user,
        alumni_user,
        jwt_auth_headers,
    ):
        """M03: Students, Recruiters, and Alumni are forbidden from accessing admin metrics."""
        url = reverse("admin-dashboard-metrics")

        for user in [student_user, recruiter_user, alumni_user]:
            api_client.credentials(**jwt_auth_headers(user))
            response = api_client.get(url)
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_request_is_unauthorized(self, api_client):
        """M04: Unauthenticated requests return 401 Unauthorized."""
        url = reverse("admin-dashboard-metrics")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_database_metrics_are_all_zero(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """M05: Clean dataset returns zero counts for all metrics (excluding IPC admin)."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-dashboard-metrics")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["active_opportunities"] == 0
        assert data["students"] == 0
        assert data["verified_recruiters"] == 0
        assert data["applications"] == 0
        assert data["pending_approvals"] == 0

    def test_active_opportunities_metric_counts_only_published_and_future_deadline(
        self,
        api_client,
        ipc_admin_user,
        jwt_auth_headers,
        verified_company,
        recruiter_user,
    ):
        """M06: Only published opportunities with future deadlines count as active."""
        now = timezone.now()

        # 1. Active opportunity: published, future deadline
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Active Job 1",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1000000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=10),
            published_at=now,
        )

        # 2. Expired opportunity: published, past deadline (should NOT count as active)
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Expired Job",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1000000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now - timezone.timedelta(days=2),
            published_at=now - timezone.timedelta(days=20),
        )

        # 3. Draft opportunity (should NOT count)
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Draft Job",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Bangalore",
            compensation=1000000,
            status=Opportunity.Status.DRAFT,
            application_deadline=now + timezone.timedelta(days=15),
        )

        # 4. Closed opportunity (should NOT count)
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Closed Job",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Bangalore",
            compensation=1000000,
            status=Opportunity.Status.CLOSED,
            application_deadline=now + timezone.timedelta(days=15),
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        response = api_client.get(reverse("admin-dashboard-metrics"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["active_opportunities"] == 1

    def test_students_metric_counts_only_active_student_role(
        self, api_client, ipc_admin_user, jwt_auth_headers, role_user_factory
    ):
        """M07: Only active users with role=STUDENT are counted in the students metric."""
        # 2 active students
        role_user_factory(role=User.Role.STUDENT, username="student_active_1")
        role_user_factory(role=User.Role.STUDENT, username="student_active_2")

        # 1 suspended student (is_active=False)
        role_user_factory(
            role=User.Role.STUDENT, username="student_suspended", is_active=False
        )

        # 1 recruiter, 1 alumni (should NOT be counted as students)
        role_user_factory(role=User.Role.RECRUITER, username="recruiter_x")
        role_user_factory(role=User.Role.ALUMNI, username="alumni_x")

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        response = api_client.get(reverse("admin-dashboard-metrics"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["students"] == 2

    def test_verified_recruiters_and_pending_companies_metric(
        self, api_client, ipc_admin_user, jwt_auth_headers, company_factory
    ):
        """M08: Verified recruiters/companies and pending companies are accurately tallied."""
        company_factory(
            name="Verified Tech",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        company_factory(
            name="Pending Corp 1",
            verification_status=Company.VerificationStatus.PENDING,
        )
        company_factory(
            name="Pending Corp 2",
            verification_status=Company.VerificationStatus.PENDING,
        )
        company_factory(
            name="Rejected Corp",
            verification_status=Company.VerificationStatus.REJECTED,
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        response = api_client.get(reverse("admin-dashboard-metrics"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["verified_recruiters"] == 1
        assert response.data["pending_companies"] == 2

    def test_pending_approvals_metric_counts_only_pending_status(
        self,
        api_client,
        ipc_admin_user,
        jwt_auth_headers,
        verified_company,
        recruiter_user,
    ):
        """M09: Pending approvals metric accurately counts opportunities awaiting IPC review."""
        now = timezone.now()

        # 2 pending approval opportunities
        for i in range(2):
            Opportunity.objects.create(
                company=verified_company,
                created_by=recruiter_user,
                title=f"Pending Review Job {i}",
                opportunity_type=Opportunity.OpportunityType.JOB,
                work_mode=Opportunity.WorkMode.REMOTE,
                location="Remote",
                compensation=1000000,
                status=Opportunity.Status.PENDING_APPROVAL,
                application_deadline=now + timezone.timedelta(days=10),
            )

        # 1 published opportunity
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Approved Job",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1000000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=10),
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        response = api_client.get(reverse("admin-dashboard-metrics"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["pending_approvals"] == 2

    def test_applications_metric_counts_all_submitted_applications(
        self,
        api_client,
        ipc_admin_user,
        jwt_auth_headers,
        verified_company,
        recruiter_user,
        role_user_factory,
    ):
        """M10: Applications count accurately sums all submitted student applications."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Developer Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1200000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
        )

        s1 = role_user_factory(role=User.Role.STUDENT, username="applicant_1")
        s2 = role_user_factory(role=User.Role.STUDENT, username="applicant_2")

        Application.objects.create(
            student=s1,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )
        Application.objects.create(
            student=s2,
            opportunity=opp,
            status=Application.Status.UNDER_REVIEW,
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        response = api_client.get(reverse("admin-dashboard-metrics"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["applications"] == 2
