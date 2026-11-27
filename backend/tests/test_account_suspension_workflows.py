import pytest
from django.urls import reverse
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.accounts.models import User


@pytest.mark.django_db
class TestAccountSuspensionWorkflows:
    """Tests the account suspension and reactivation workflows (R3)."""

    def test_ipc_admin_suspends_active_student_successfully(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """S01: Authorized IPC admin suspends an active user account."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-suspend", kwargs={"id": student_user.id})

        reason = "Violation of campus recruitment code of conduct."
        response = api_client.post(url, {"reason": reason}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False
        assert response.data["action"] == "SUSPENDED"
        assert response.data["performed_by"] == ipc_admin_user.id

        # Verify database update
        student_user.refresh_from_db()
        assert student_user.is_active is False

        # Verify audit log
        logs = get_audit_logs()
        assert len(logs) >= 1
        suspend_log = next(log for log in logs if log["action"] == "USER_SUSPENDED")
        assert suspend_log["actor_id"] == ipc_admin_user.id
        assert suspend_log["target_id"] == str(student_user.id)
        assert suspend_log["details"]["reason"] == reason

    def test_suspended_user_is_prevented_from_logging_in(
        self, api_client, student_user
    ):
        """S02: Suspended users cannot authenticate via login endpoint."""
        student_user.is_active = False
        student_user.save()

        login_url = reverse("token-obtain-pair")
        response = api_client.post(
            login_url,
            {"username": student_user.username, "password": "test-only-password"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_suspended_user_cannot_access_protected_apis(
        self, api_client, student_user, jwt_auth_headers
    ):
        """S03: Suspended users are rejected from accessing protected API endpoints."""
        headers = jwt_auth_headers(student_user)
        api_client.credentials(**headers)

        # Deactivate user
        student_user.is_active = False
        student_user.save()

        me_url = reverse("account-profile")
        response = api_client.get(me_url)

        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_ipc_admin_reactivates_suspended_account(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """S04: Authorized IPC admin reactivates a suspended user account."""
        student_user.is_active = False
        student_user.save()

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-reactivate", kwargs={"id": student_user.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is True
        assert response.data["action"] == "REACTIVATED"

        student_user.refresh_from_db()
        assert student_user.is_active is True

        logs = get_audit_logs()
        reactivate_log = next(log for log in logs if log["action"] == "USER_REACTIVATED")
        assert reactivate_log["target_id"] == str(student_user.id)

    def test_suspending_already_suspended_user_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """S05: Attempting to suspend an already suspended account returns 400."""
        student_user.is_active = False
        student_user.save()

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-suspend", kwargs={"id": student_user.id})

        response = api_client.post(url, {"reason": "Duplicate suspend"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already suspended" in str(response.data)

    def test_reactivating_active_user_returns_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """S06: Attempting to reactivate an active account returns 400."""
        assert student_user.is_active is True

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-reactivate", kwargs={"id": student_user.id})

        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not suspended" in str(response.data)

    def test_administrator_cannot_suspend_themselves(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """S07: Administrators are forbidden from self-suspension."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-suspend", kwargs={"id": ipc_admin_user.id})

        response = api_client.post(url, {"reason": "Self-suspend attempt"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot suspend their own account" in str(response.data)

        ipc_admin_user.refresh_from_db()
        assert ipc_admin_user.is_active is True

    def test_ipc_admin_cannot_suspend_system_admin(
        self, api_client, ipc_admin_user, jwt_auth_headers, system_admin_user
    ):
        """S08: IPC administrator cannot suspend a System Administrator account."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-suspend", kwargs={"id": system_admin_user.id})

        response = api_client.post(url, {"reason": "Unauthorized admin suspend"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        system_admin_user.refresh_from_db()
        assert system_admin_user.is_active is True

    def test_nonexistent_user_id_returns_404(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """S09: Nonexistent user ID returns 404."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-user-suspend", kwargs={"id": 999999})

        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
