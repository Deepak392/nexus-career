import pytest
from django.urls import reverse
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.accounts.models import User
from apps.alumni.models import AlumniProfile
from apps.recruiters.models import Company


@pytest.mark.django_db
class TestAuthenticationAndRolePermissions:
    """Validates Deepak's JWT authentication and shared role-based permissions

    for IPC administrative endpoints.
    """

    def test_unauthenticated_request_is_rejected_with_401(
        self, api_client, pending_recruiter, pending_alumni_profile
    ):
        """A01: No credentials supplied to protected IPC verification endpoints."""
        recruiter_url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        alumni_url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        rec_response = api_client.post(recruiter_url, {"status": "VERIFIED"}, format="json")
        alm_response = api_client.post(alumni_url, {"status": "VERIFIED"}, format="json")

        assert rec_response.status_code == status.HTTP_401_UNAUTHORIZED
        assert alm_response.status_code == status.HTTP_401_UNAUTHORIZED

        # Assert no database mutation and no audit entry
        pending_recruiter.company.refresh_from_db()
        pending_alumni_profile.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.PENDING
        assert pending_alumni_profile.verification_status == AlumniProfile.VerificationStatus.PENDING
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
        self, api_client, student_user, jwt_auth_headers, pending_recruiter, pending_alumni_profile
    ):
        """P01: Authenticated student attempts recruiter and alumni verification."""
        headers = jwt_auth_headers(student_user)
        api_client.credentials(**headers)

        rec_url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        alm_url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        rec_response = api_client.post(rec_url, {"status": "VERIFIED"}, format="json")
        alm_response = api_client.post(alm_url, {"status": "VERIFIED"}, format="json")

        assert rec_response.status_code == status.HTTP_403_FORBIDDEN
        assert alm_response.status_code == status.HTTP_403_FORBIDDEN

        # Assert no state change
        pending_recruiter.company.refresh_from_db()
        pending_alumni_profile.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.PENDING
        assert pending_alumni_profile.verification_status == AlumniProfile.VerificationStatus.PENDING
        assert len(get_audit_logs()) == 0

    def test_recruiter_role_cannot_verify_any_company_including_own(
        self, api_client, recruiter_user, jwt_auth_headers, pending_recruiter
    ):
        """P02 / V03: Recruiter attempts to verify their own company."""
        headers = jwt_auth_headers(recruiter_user)
        api_client.credentials(**headers)

        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        response = api_client.post(url, {"status": "VERIFIED"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        pending_recruiter.company.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.PENDING
        assert len(get_audit_logs()) == 0

    def test_alumni_role_is_denied_with_403(
        self, api_client, alumni_user, jwt_auth_headers, pending_recruiter, pending_alumni_profile
    ):
        """P03: Alumni user attempts administrative verification."""
        headers = jwt_auth_headers(alumni_user)
        api_client.credentials(**headers)

        rec_url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        alm_url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        rec_response = api_client.post(rec_url, {"status": "VERIFIED"}, format="json")
        alm_response = api_client.post(alm_url, {"status": "VERIFIED"}, format="json")

        assert rec_response.status_code == status.HTTP_403_FORBIDDEN
        assert alm_response.status_code == status.HTTP_403_FORBIDDEN
        assert len(get_audit_logs()) == 0

    def test_system_admin_is_denied_ipc_verification_under_role_isolation_policy(
        self, api_client, system_admin_user, jwt_auth_headers, pending_recruiter, pending_alumni_profile
    ):
        """P06: System admin cannot perform IPC verification without explicit IPC delegation."""
        headers = jwt_auth_headers(system_admin_user)
        api_client.credentials(**headers)

        rec_url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})
        alm_url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        rec_response = api_client.post(rec_url, {"status": "VERIFIED"}, format="json")
        alm_response = api_client.post(alm_url, {"status": "VERIFIED"}, format="json")

        assert rec_response.status_code == status.HTTP_403_FORBIDDEN
        assert alm_response.status_code == status.HTTP_403_FORBIDDEN
        assert len(get_audit_logs()) == 0

    def test_inactive_or_suspended_account_is_blocked(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """A05: Suspended or inactive user with otherwise valid credentials."""
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
