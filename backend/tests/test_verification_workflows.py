import pytest
from django.urls import reverse
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.alumni.models import AlumniProfile
from apps.recruiters.models import Company


@pytest.mark.django_db
class TestRecruiterVerificationWorkflow:
    """Tests the IPC administrative decision workflow for recruiters and companies."""

    def test_ipc_admin_verifies_pending_recruiter_successfully(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """V01: IPC admin approves an eligible pending recruiter/company."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == Company.VerificationStatus.VERIFIED
        assert response.data["verified_by"] == ipc_admin_user.id
        assert response.data["verified_at"] is not None

        # Assert database persistence
        pending_recruiter.company.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.VERIFIED
        assert pending_recruiter.company.verified_by == ipc_admin_user
        assert pending_recruiter.company.verified_at is not None

        # Assert audit dispatch
        logs = get_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "RECRUITER_VERIFICATION_VERIFIED"
        assert logs[0]["actor_id"] == ipc_admin_user.id
        assert logs[0]["target_id"] == str(pending_recruiter.company.id)
        assert logs[0]["target_type"] == "Company"

    def test_ipc_admin_rejects_pending_recruiter_with_reason(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """V02: IPC admin rejects an ineligible recruiter with mandatory reason."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})

        reason = "Official company registration documents were unverified."
        response = api_client.post(
            url,
            {"status": "REJECTED", "rejection_reason": reason},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == Company.VerificationStatus.REJECTED
        assert response.data["rejection_reason"] == reason

        # Assert database state
        pending_recruiter.company.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.REJECTED
        assert pending_recruiter.company.verified_by == ipc_admin_user

        # Assert audit record
        logs = get_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "RECRUITER_VERIFICATION_REJECTED"
        assert logs[0]["details"]["rejection_reason"] == reason

    def test_rejection_without_reason_is_rejected_with_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """V03: Rejecting without explanation triggers validation error."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})

        response = api_client.post(url, {"status": "REJECTED", "rejection_reason": ""}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rejection_reason" in response.data

        # Database remains untouched
        pending_recruiter.company.refresh_from_db()
        assert pending_recruiter.company.verification_status == Company.VerificationStatus.PENDING
        assert len(get_audit_logs()) == 0

    def test_nonexistent_recruiter_id_returns_404(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """V04: Nonexistent recruiter or company ID."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": 999999})

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(get_audit_logs()) == 0

    def test_disallowed_status_transition_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """V05 / V06: Re-verifying an already VERIFIED or REJECTED company is blocked."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})

        # Pre-set company to VERIFIED
        pending_recruiter.company.verification_status = Company.VerificationStatus.VERIFIED
        pending_recruiter.company.save()

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Disallowed status transition" in response.data["detail"]
        assert len(get_audit_logs()) == 0

    def test_unsupported_decision_status_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_recruiter
    ):
        """V07: Request contains unsupported status."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-recruiter-verify", kwargs={"id": pending_recruiter.id})

        response = api_client.post(url, {"status": "SUSPENDED"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert len(get_audit_logs()) == 0


@pytest.mark.django_db
class TestAlumniVerificationWorkflow:
    """Tests the IPC administrative decision workflow for alumni profiles and graduation proof."""

    def test_ipc_admin_verifies_pending_alumnus_successfully(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_alumni_profile
    ):
        """V08: IPC admin approves an eligible pending alumnus profile."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == AlumniProfile.VerificationStatus.VERIFIED
        assert response.data["user_id"] == pending_alumni_profile.user_id

        # Assert database persistence
        pending_alumni_profile.refresh_from_db()
        assert pending_alumni_profile.verification_status == AlumniProfile.VerificationStatus.VERIFIED

        # Assert audit dispatch
        logs = get_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "ALUMNI_VERIFICATION_VERIFIED"
        assert logs[0]["actor_id"] == ipc_admin_user.id
        assert logs[0]["target_id"] == str(pending_alumni_profile.id)
        assert logs[0]["target_type"] == "AlumniProfile"

    def test_ipc_admin_rejects_pending_alumnus_with_reason(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_alumni_profile
    ):
        """V09: IPC admin rejects an alumnus with invalid graduation evidence."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        reason = "Submitted graduation degree certificate was illegible."
        response = api_client.post(
            url,
            {"status": "REJECTED", "rejection_reason": reason},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == AlumniProfile.VerificationStatus.REJECTED
        assert response.data["rejection_reason"] == reason

        pending_alumni_profile.refresh_from_db()
        assert pending_alumni_profile.verification_status == AlumniProfile.VerificationStatus.REJECTED

        logs = get_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "ALUMNI_VERIFICATION_REJECTED"
        assert logs[0]["details"]["rejection_reason"] == reason

    def test_alumni_rejection_without_reason_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_alumni_profile
    ):
        """V10: Rejecting an alumnus without explanation fails validation."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        response = api_client.post(url, {"status": "REJECTED", "rejection_reason": ""}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rejection_reason" in response.data
        assert len(get_audit_logs()) == 0

    def test_nonexistent_alumnus_id_returns_404(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """V11: Nonexistent alumnus profile ID."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-alumni-verify", kwargs={"id": 888888})

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(get_audit_logs()) == 0

    def test_disallowed_alumni_status_transition_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, pending_alumni_profile
    ):
        """V12: Re-verifying an already VERIFIED or REJECTED alumnus profile is blocked."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-alumni-verify", kwargs={"id": pending_alumni_profile.id})

        pending_alumni_profile.verification_status = AlumniProfile.VerificationStatus.VERIFIED
        pending_alumni_profile.save()

        response = api_client.post(url, {"status": "VERIFIED"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Disallowed status transition" in response.data["detail"]
        assert len(get_audit_logs()) == 0
