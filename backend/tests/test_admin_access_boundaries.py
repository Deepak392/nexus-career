"""R7: Admin Access-Boundary & Negative Security Test Suite.

Covers:
1. Cross-company access denial (Recruiter A vs Company B/Recruiter B).
2. Unauthorized opportunity approval & rejection denial (Student, Recruiter, Alumni, Anonymous).
3. System Admin versus IPC Admin separation and hierarchy guards.
4. Additional permission & security boundary tests (missing auth, invalid token, suspended accounts, ID manipulation).
5. Permission Matrix test coverage.
"""

from datetime import timedelta
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.models import User
from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile


@pytest.fixture
def boundary_test_setup(role_user_factory, db):
    """Sets up two separate companies with recruiters, an IPC admin, a system admin, and a student."""
    ipc_admin = role_user_factory("IPC Admin", username="boundary_ipc_admin")
    sys_admin = role_user_factory("System Admin", username="boundary_sys_admin")
    recruiter_a = role_user_factory("Recruiter", username="boundary_recruiter_a")
    recruiter_b = role_user_factory("Recruiter", username="boundary_recruiter_b")
    student_1 = role_user_factory("Student", username="boundary_student_1")
    alumni_1 = role_user_factory("Alumni", username="boundary_alumni_1")

    company_a = Company.objects.create(
        name="Nexus Technologies A",
        industry="Software",
        contact_email="recruiter_a@nexus-tech-a.test",
        verification_status=Company.VerificationStatus.VERIFIED,
    )
    company_b = Company.objects.create(
        name="Apex Logistics B",
        industry="Supply Chain",
        contact_email="recruiter_b@apex-b.test",
        verification_status=Company.VerificationStatus.VERIFIED,
    )

    RecruiterProfile.objects.create(user=recruiter_a, company=company_a)
    RecruiterProfile.objects.create(user=recruiter_b, company=company_b)

    now = timezone.now()

    opp_a = Opportunity.objects.create(
        company=company_a,
        created_by=recruiter_a,
        title="Backend Engineer A",
        description="Core systems developer at Company A",
        opportunity_type=Opportunity.OpportunityType.JOB,
        work_mode=Opportunity.WorkMode.REMOTE,
        location="Bengaluru",
        application_deadline=now + timedelta(days=20),
        status=Opportunity.Status.DRAFT,
    )

    opp_b = Opportunity.objects.create(
        company=company_b,
        created_by=recruiter_b,
        title="Supply Chain Specialist B",
        description="Operations at Company B",
        opportunity_type=Opportunity.OpportunityType.JOB,
        work_mode=Opportunity.WorkMode.ONSITE,
        location="Mumbai",
        application_deadline=now + timedelta(days=20),
        status=Opportunity.Status.DRAFT,
    )

    return {
        "ipc_admin": ipc_admin,
        "sys_admin": sys_admin,
        "recruiter_a": recruiter_a,
        "recruiter_b": recruiter_b,
        "student_1": student_1,
        "alumni_1": alumni_1,
        "company_a": company_a,
        "company_b": company_b,
        "opp_a": opp_a,
        "opp_b": opp_b,
    }


@pytest.mark.django_db
class TestCrossCompanyAccessBoundaries:
    """7.1 Cross-company access tests: Verifies complete tenant data isolation."""

    def test_recruiter_cannot_view_another_company_profile(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B calling company profile endpoint sees only Company B, never Company A."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        url = reverse("recruiter-company-profile")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Apex Logistics B"
        assert response.data["name"] != "Nexus Technologies A"

    def test_recruiter_cannot_modify_another_company_profile(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B calling patch company profile modifies only Company B."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        url = reverse("recruiter-company-profile")

        response = api_client.patch(url, {"name": "Apex Logistics B Updated"})

        assert response.status_code == status.HTTP_200_OK
        boundary_test_setup["company_a"].refresh_from_db()
        assert boundary_test_setup["company_a"].name == "Nexus Technologies A"  # Untouched

    def test_recruiter_cannot_view_another_company_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B cannot view Company A's draft opportunity via recruiter detail endpoint."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        opp_a_id = boundary_test_setup["opp_a"].id
        url = reverse("recruiter-opportunity-detail", kwargs={"pk": opp_a_id})

        response = api_client.get(url)

        # Returns 404 to avoid leaking existence of the object
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_recruiter_cannot_modify_another_company_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B cannot modify Company A's opportunity via PATCH."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        opp_a_id = boundary_test_setup["opp_a"].id
        url = reverse("recruiter-opportunity-detail", kwargs={"pk": opp_a_id})

        response = api_client.patch(url, {"title": "Compromised Title"})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        boundary_test_setup["opp_a"].refresh_from_db()
        assert boundary_test_setup["opp_a"].title == "Backend Engineer A"

    def test_recruiter_cannot_close_another_company_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B cannot close Company A's opportunity."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        opp_a_id = boundary_test_setup["opp_a"].id
        url = reverse("recruiter-opportunity-close", kwargs={"pk": opp_a_id})

        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_recruiter_opportunity_listing_excludes_other_companies(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter B listing opportunities sees only Company B's listings."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        url = reverse("recruiter-opportunity-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data if isinstance(response.data, list) else response.data.get("results", [])
        retrieved_ids = [r["id"] for r in results]
        assert boundary_test_setup["opp_b"].id in retrieved_ids
        assert boundary_test_setup["opp_a"].id not in retrieved_ids


@pytest.mark.django_db
class TestUnauthorizedOpportunityApprovals:
    """7.2 Unauthorized opportunity approval & rejection tests."""

    def test_student_cannot_approve_or_reject_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Student role is strictly forbidden from approval and rejection endpoints."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["student_1"]))
        opp_id = boundary_test_setup["opp_a"].id

        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp_id})
        reject_url = reverse("admin-opportunity-reject", kwargs={"id": opp_id})

        resp_approve = api_client.post(approve_url)
        assert resp_approve.status_code == status.HTTP_403_FORBIDDEN

        resp_reject = api_client.post(reject_url, {"rejection_reason": "Invalid opportunity"})
        assert resp_reject.status_code == status.HTTP_403_FORBIDDEN

    def test_recruiter_cannot_approve_own_or_other_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter cannot approve their own or another company's opportunity."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_a"]))
        opp_a_id = boundary_test_setup["opp_a"].id
        opp_b_id = boundary_test_setup["opp_b"].id

        approve_a = reverse("admin-opportunity-approve", kwargs={"id": opp_a_id})
        approve_b = reverse("admin-opportunity-approve", kwargs={"id": opp_b_id})

        assert api_client.post(approve_a).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.post(approve_b).status_code == status.HTTP_403_FORBIDDEN

    def test_alumni_cannot_approve_opportunity(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Alumni account is denied approval operations."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["alumni_1"]))
        opp_id = boundary_test_setup["opp_a"].id
        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp_id})

        assert api_client.post(approve_url).status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_request_is_denied_with_401(
        self, api_client, boundary_test_setup
    ):
        """Unauthenticated direct API calls receive 401 Unauthorized."""
        opp_id = boundary_test_setup["opp_a"].id
        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp_id})

        response = api_client.post(approve_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSystemAdminVsIPCAdminSeparation:
    """7.3 System Admin versus IPC Admin separation and hierarchy guards."""

    def test_ipc_admin_cannot_suspend_system_admin(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """IPC Admin attempting to suspend a System Admin account receives 403 Forbidden."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["ipc_admin"]))
        sys_admin_id = boundary_test_setup["sys_admin"].id
        url = reverse("admin-user-suspend", kwargs={"id": sys_admin_id})

        response = api_client.post(url, {"reason": "Testing hierarchy limits"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        # The view raises PermissionDenied: "IPC administrators cannot suspend System Administrator accounts."
        assert "System Administrator" in str(response.data)

        boundary_test_setup["sys_admin"].refresh_from_db()
        assert boundary_test_setup["sys_admin"].is_active is True

    def test_ipc_admin_cannot_suspend_themselves(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """IPC Admin cannot self-suspend their own administrative account."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["ipc_admin"]))
        ipc_admin_id = boundary_test_setup["ipc_admin"].id
        url = reverse("admin-user-suspend", kwargs={"id": ipc_admin_id})

        response = api_client.post(url, {"reason": "Self suspension attempt"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # The view raises ValidationError: "Administrators cannot suspend their own account."
        assert "suspend" in str(response.data).lower()

    def test_non_admin_roles_denied_from_all_ipc_endpoints(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Students and Recruiters are forbidden from all /api/v1/admin/ endpoints."""
        endpoints = [
            ("GET", reverse("admin-dashboard-metrics")),
            ("GET", reverse("admin-audit-logs")),
            ("GET", reverse("admin-recruiter-pending")),
            ("GET", reverse("admin-opportunity-pending")),
            ("GET", reverse("admin-reports-list")),
            ("GET", reverse("admin-reports-export")),
        ]

        for user in [boundary_test_setup["student_1"], boundary_test_setup["recruiter_a"], boundary_test_setup["alumni_1"]]:
            api_client.credentials(**jwt_auth_headers(user))
            for method, url in endpoints:
                resp = api_client.get(url) if method == "GET" else api_client.post(url)
                assert resp.status_code == status.HTTP_403_FORBIDDEN, f"Failed for {user.username} on {url}"


@pytest.mark.django_db
class TestAdditionalBoundarySecurityGuards:
    """7.5 Additional permission, suspended account, and ID manipulation guards."""

    def test_missing_auth_header_returns_401(self, api_client):
        """Protected endpoints return 401 Unauthorized when Authorization header is absent."""
        urls = [
            reverse("admin-dashboard-metrics"),
            reverse("admin-reports-list"),
            reverse("student-profile"),
            reverse("recruiter-company-profile"),
        ]
        for url in urls:
            assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_bearer_token_returns_401(self, api_client):
        """Malformed or fabricated JWT token is rejected with 401."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token-signature-here")
        url = reverse("admin-dashboard-metrics")
        assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED

    def test_suspended_account_is_blocked_from_all_operations(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """A user account deactivated/suspended cannot access any authenticated API."""
        student = boundary_test_setup["student_1"]
        student.is_active = False
        student.save(update_fields=["is_active"])

        api_client.credentials(**jwt_auth_headers(student))
        url = reverse("student-profile")

        response = api_client.get(url)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_id_manipulation_does_not_reveal_protected_resources(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Accessing a non-existent or foreign ID returns 404 rather than revealing existence."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_b"]))
        non_existent_url = reverse("recruiter-opportunity-detail", kwargs={"pk": 999999})
        response = api_client.get(non_existent_url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_student_cannot_access_recruiter_endpoints(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Student is forbidden from recruiter-only management routes."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["student_1"]))
        url = reverse("recruiter-company-profile")
        assert api_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    def test_recruiter_cannot_apply_for_opportunities(
        self, api_client, boundary_test_setup, jwt_auth_headers
    ):
        """Recruiter is forbidden from student application endpoints."""
        api_client.credentials(**jwt_auth_headers(boundary_test_setup["recruiter_a"]))
        url = reverse("application-list")
        assert api_client.post(url, {"opportunity_id": 1}).status_code == status.HTTP_403_FORBIDDEN
