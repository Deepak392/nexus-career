import pytest
from django.urls import reverse
from rest_framework import status

from api.core import audit
from apps.accounts.models import User
from apps.recruiters.models import WorkflowAuditEvent


@pytest.mark.django_db
class TestAuditTrailViews:
    """Tests the authorized audit trail viewing API (R4)."""

    def test_ipc_admin_can_view_audit_logs(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """L01: Authorized IPC administrator retrieves audit events with actor, action, target, time."""
        # Seed several audit events
        audit.log(
            actor=ipc_admin_user,
            action="USER_SUSPENDED",
            target=student_user,
            context={"reason": "Audit verification test"},
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-audit-logs")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) >= 1

        entry = results[0]
        assert "actor" in entry
        assert entry["actor"]["id"] == ipc_admin_user.id
        assert entry["actor"]["username"] == ipc_admin_user.username
        assert entry["action"] == "USER_SUSPENDED"
        assert "target" in entry
        assert "created_at" in entry
        assert "details" in entry

    def test_sensitive_credentials_are_not_exposed(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """L02: Passwords, tokens, and secrets are stripped and not exposed in audit log details."""
        audit.log(
            actor=ipc_admin_user,
            action="USER_AUTHENTICATED",
            target=student_user,
            context={
                "password": "super-secret-password",
                "token": "secret-jwt-token",
                "safe_field": "public-metadata",
            },
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-audit-logs")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        entry = next(e for e in results if e["action"] == "USER_AUTHENTICATED")

        assert "password" not in entry["details"]
        assert "token" not in entry["details"]
        assert entry["details"].get("safe_field") == "public-metadata"

    def test_filter_by_action(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """L03: Filtering by action parameter returns only matching entries."""
        audit.log(actor=ipc_admin_user, action="ACTION_ALPHA", target=student_user, context={})
        audit.log(actor=ipc_admin_user, action="ACTION_BETA", target=student_user, context={})

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = f"{reverse('admin-audit-logs')}?action=ACTION_ALPHA"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert all(e["action"] == "ACTION_ALPHA" for e in results)
        assert any(e["action"] == "ACTION_ALPHA" for e in results)

    def test_filter_by_actor(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user, role_user_factory
    ):
        """L04: Filtering by actor username returns events performed by that actor."""
        admin2 = role_user_factory("IPC Admin", username="second-admin")
        audit.log(actor=ipc_admin_user, action="EVENT_A", target=student_user, context={})
        audit.log(actor=admin2, action="EVENT_B", target=student_user, context={})

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = f"{reverse('admin-audit-logs')}?actor=second-admin"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert all(e["actor"]["username"] == "second-admin" for e in results)

    def test_pagination_conforms_to_page_size_and_limits(
        self, api_client, ipc_admin_user, jwt_auth_headers, student_user
    ):
        """L05: Pagination supports page and page_size query parameters."""
        for i in range(15):
            audit.log(actor=ipc_admin_user, action=f"BATCH_{i}", target=student_user, context={})

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = f"{reverse('admin-audit-logs')}?page_size=5&page=1"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert len(response.data["results"]) == 5
        assert "next" in response.data

    def test_audit_logs_endpoint_is_read_only(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """L06: Modification or deletion through the viewing API is forbidden (405)."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-audit-logs")

        resp_post = api_client.post(url, {}, format="json")
        resp_put = api_client.put(url, {}, format="json")
        resp_delete = api_client.delete(url)

        assert resp_post.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp_put.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp_delete.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
