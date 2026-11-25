import pytest
from django.urls import reverse
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.accounts.models import User
from apps.alumni.models import AlumniProfile
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company


@pytest.mark.django_db
class TestAuthenticationAndRolePermissions:
    """Validates JWT authentication and shared role-based permissions

    for all IPC administrative endpoints (R1, R2, R3, R4).
    """

    def test_unauthenticated_requests_are_rejected_with_401(
        self, api_client, pending_recruiter, pending_alumni_profile, opportunity_factory, student_user
    ):
        """A01: No credentials supplied to protected IPC administration endpoints."""
        opp = opportunity_factory()
        endpoints = [
            reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id}),
            reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id}),
            reverse("admin-opportunity-approve", kwargs={"id": opp.id}),
            reverse("admin-opportunity-reject", kwargs={"id": opp.id}),
            reverse("admin-user-suspend", kwargs={"id": student_user.id}),
            reverse("admin-user-reactivate", kwargs={"id": student_user.id}),
            reverse("admin-audit-logs"),
        ]

        for ep in endpoints:
            if "audit-logs" in ep:
                resp = api_client.get(ep)
            else:
                resp = api_client.post(ep, {"status": "VERIFIED"}, format="json")
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED, f"Expected 401 for {ep}, got {resp.status_code}"

        assert len(get_audit_logs()) == 0

    def test_invalid_jwt_token_is_rejected_with_401(
        self, api_client, pending_recruiter
    ):
        """A04: Malformed or invalid JWT token."""
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token-value-xyz")

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert len(get_audit_logs()) == 0

    def test_student_role_is_denied_with_403(
        self, api_client, student_user, jwt_auth_headers, pending_recruiter, pending_alumni_profile, opportunity_factory
    ):
        """P01: Authenticated student attempts administrative operations."""
        opp = opportunity_factory()
        headers = jwt_auth_headers(student_user)
        api_client.credentials(**headers)

        endpoints = [
            (reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id}), "post", {"status": "VERIFIED"}),
            (reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id}), "post", {"status": "VERIFIED"}),
            (reverse("admin-opportunity-approve", kwargs={"id": opp.id}), "post", {}),
            (reverse("admin-opportunity-reject", kwargs={"id": opp.id}), "post", {"reason": "Test"}),
            (reverse("admin-user-suspend", kwargs={"id": student_user.id}), "post", {}),
            (reverse("admin-audit-logs"), "get", None),
        ]

        for ep, method, data in endpoints:
            if method == "get":
                resp = api_client.get(ep)
            else:
                resp = api_client.post(ep, data, format="json")
            assert resp.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403 for {ep}, got {resp.status_code}"

        assert len(get_audit_logs()) == 0

    def test_recruiter_role_is_denied_administrative_actions(
        self, api_client, recruiter_user, jwt_auth_headers, pending_recruiter, opportunity_factory
    ):
        """P02: Recruiter attempts to verify companies, approve opportunities, or view audit logs."""
        opp = opportunity_factory()
        headers = jwt_auth_headers(recruiter_user)
        api_client.credentials(**headers)

        # Attempt verifying own recruiter profile
        resp1 = api_client.post(
            reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id}),
            {"status": "VERIFIED"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        # Attempt approving opportunity
        resp2 = api_client.post(
            reverse("admin-opportunity-approve", kwargs={"id": opp.id}),
            {},
            format="json",
        )
        assert resp2.status_code == status.HTTP_403_FORBIDDEN

        # Attempt viewing audit logs
        resp3 = api_client.get(reverse("admin-audit-logs"))
        assert resp3.status_code == status.HTTP_403_FORBIDDEN

        assert len(get_audit_logs()) == 0

    def test_alumni_role_is_denied_administrative_actions(
        self, api_client, alumni_user, jwt_auth_headers, pending_alumni_profile
    ):
        """P03: Alumni user attempts administrative verification or audit log viewing."""
        headers = jwt_auth_headers(alumni_user)
        api_client.credentials(**headers)

        resp1 = api_client.post(
            reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id}),
            {"status": "VERIFIED"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        resp2 = api_client.get(reverse("admin-audit-logs"))
        assert resp2.status_code == status.HTTP_403_FORBIDDEN

        assert len(get_audit_logs()) == 0

    def test_suspended_account_is_blocked_from_protected_operations(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """A05: Suspended or inactive user with valid JWT token is blocked."""
        headers = jwt_auth_headers(ipc_admin_user)
        api_client.credentials(**headers)

        # Deactivate user to simulate suspension
        ipc_admin_user.is_active = False
        ipc_admin_user.save()

        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        response = api_client.post(url, {"status": "VERIFIED"}, format="json")

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        pending_recruiter.company.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.PENDING
        assert len(get_audit_logs()) == 0

    def test_authorized_ipc_admin_is_granted_access(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """A02 / P04: Valid IPC administrator credentials with JWT Bearer auth."""
        headers = jwt_auth_headers(ipc_admin_user)
        api_client.credentials(**headers)

        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        response = api_client.post(url, {"status": "VERIFIED"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == Company.VerificationStatus.VERIFIED
        assert response.data["verified_by"] == ipc_admin_user.id
