import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core.audit import get_audit_logs
from api.core.events import get_emitted_events
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company


@pytest.mark.django_db
class TestOpportunityApprovalWorkflows:
    """Tests the IPC administrative approval and rejection workflow for opportunities (R2)."""

    def test_ipc_admin_approves_pending_opportunity_successfully(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O01: Authorized IPC administrator approves a valid pending opportunity."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        opp = opportunity_factory(status=Opportunity.Status.PENDING_APPROVAL)
        url = reverse("admin-opportunity-approve", kwargs={"id": opp.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Opportunity.Status.PUBLISHED

        # Assert database updates
        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PUBLISHED
        assert opp.approved_by == ipc_admin_user
        assert opp.approved_at is not None
        assert opp.published_at is not None

        # Assert audit log
        logs = get_audit_logs()
        assert len(logs) >= 1
        approve_log = next(log for log in logs if log["action"] == "OPPORTUNITY_APPROVED")
        assert approve_log["actor_id"] == ipc_admin_user.id
        assert approve_log["target_id"] == str(opp.id)

        # Assert recruiter notification event emitted
        events = get_emitted_events()
        assert len(events) >= 1
        opp_event = next(ev for ev in events if ev["event_type"] == "OPPORTUNITY_APPROVED")
        assert opp_event["payload"]["opportunity_id"] == opp.id
        assert opp_event["payload"]["recipient_id"] == opp.created_by_id
        assert opp_event["payload"]["decision"] == "APPROVED"

    def test_ipc_admin_rejects_pending_opportunity_with_reason(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O02: Authorized IPC administrator rejects an opportunity with valid explanation."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        opp = opportunity_factory(status=Opportunity.Status.PENDING_APPROVAL)
        url = reverse("admin-opportunity-reject", kwargs={"id": opp.id})

        reason = "Compensation criteria does not meet university minimum standards."
        response = api_client.post(url, {"reason": reason}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == Opportunity.Status.REJECTED

        # Assert database persistence
        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.REJECTED
        assert opp.rejection_reason == reason
        assert opp.approved_by is None

        # Assert audit log
        logs = get_audit_logs()
        reject_log = next(log for log in logs if log["action"] == "OPPORTUNITY_REJECTED")
        assert reject_log["details"]["reason"] == reason

        # Assert recruiter notification event emitted
        events = get_emitted_events()
        opp_event = next(ev for ev in events if ev["event_type"] == "OPPORTUNITY_REJECTED")
        assert opp_event["payload"]["opportunity_id"] == opp.id
        assert opp_event["payload"]["recipient_id"] == opp.created_by_id
        assert opp_event["payload"]["decision"] == "REJECTED"
        assert opp_event["payload"]["reason"] == reason

    def test_rejection_without_reason_is_rejected_with_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O03: Rejection without an explanatory reason fails validation."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        opp = opportunity_factory(status=Opportunity.Status.PENDING_APPROVAL)
        url = reverse("admin-opportunity-reject", kwargs={"id": opp.id})

        response = api_client.post(url, {"reason": ""}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reason" in response.data

        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PENDING_APPROVAL
        assert len(get_audit_logs()) == 0
        assert len(get_emitted_events()) == 0

    def test_approval_fails_if_company_is_not_verified(
        self, api_client, ipc_admin_user, jwt_auth_headers, company_factory, recruiter_user, opportunity_factory
    ):
        """O04: An opportunity belonging to an unverified company cannot be approved."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        unverified_company = company_factory(verification_status=Company.VerificationStatus.PENDING)
        opp = opportunity_factory(company=unverified_company, status=Opportunity.Status.PENDING_APPROVAL)

        url = reverse("admin-opportunity-approve", kwargs={"id": opp.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "company must be verified" in str(response.data)

        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PENDING_APPROVAL
        assert len(get_audit_logs()) == 0
        assert len(get_emitted_events()) == 0

    def test_approval_fails_if_application_deadline_is_expired(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O05: Opportunities with expired application deadlines cannot be approved."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        past_deadline = timezone.now() - timezone.timedelta(days=1)
        opp = opportunity_factory(
            application_deadline=past_deadline,
            status=Opportunity.Status.PENDING_APPROVAL,
        )

        url = reverse("admin-opportunity-approve", kwargs={"id": opp.id})
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "application_deadline" in response.data or "detail" in response.data

        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PENDING_APPROVAL
        assert len(get_audit_logs()) == 0
        assert len(get_emitted_events()) == 0

    def test_disallowed_lifecycle_transitions_are_rejected_with_400(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O06: Approving or rejecting a non-pending opportunity is rejected."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        opp = opportunity_factory(status=Opportunity.Status.DRAFT)

        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp.id})
        reject_url = reverse("admin-opportunity-reject", kwargs={"id": opp.id})

        resp_approve = api_client.post(approve_url, {}, format="json")
        resp_reject = api_client.post(reject_url, {"reason": "Not ready"}, format="json")

        assert resp_approve.status_code == status.HTTP_400_BAD_REQUEST
        assert resp_reject.status_code == status.HTTP_400_BAD_REQUEST
        assert len(get_audit_logs()) == 0
        assert len(get_emitted_events()) == 0

    def test_nonexistent_opportunity_id_returns_404(
        self, api_client, ipc_admin_user, jwt_auth_headers
    ):
        """O07: Nonexistent opportunity ID."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        url = reverse("admin-opportunity-approve", kwargs={"id": 999999})

        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert len(get_audit_logs()) == 0

    def test_ipc_url_aliases_work_consistently(
        self, api_client, ipc_admin_user, jwt_auth_headers, opportunity_factory
    ):
        """O08: /api/v1/ipc/opportunities/{pk}/approve/ and reject/ endpoints function identically."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        opp = opportunity_factory(status=Opportunity.Status.PENDING_APPROVAL)

        ipc_url = reverse("ipc-opportunity-approve", kwargs={"pk": opp.id})
        response = api_client.post(ipc_url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PUBLISHED
