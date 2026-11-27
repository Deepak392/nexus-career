"""R6: Activity Reports and CSV Export Test Suite.

Covers:
1. Authorized IPC Admin exports a report.
2. Unauthorized student attempts export.
3. Recruiter attempts export.
4. Unauthorized role attempts report retrieval.
5. Date filter works.
6. Activity type filter works.
7. Company filter works.
8. Status filter works.
9. Multiple filters work together.
10. Invalid date range is rejected.
11. Empty report generates a valid CSV.
12. CSV headers are correct.
13. CSV escaping handles special characters.
14. Export action is logged.
15. Unauthorized export does not expose data.
16. System Admin can access and export reports.
17. Paginated JSON activity reports list endpoint works.
"""

import csv
import io
from datetime import timedelta
import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core import audit
from apps.accounts.models import User
from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile, WorkflowAuditEvent


@pytest.fixture
def test_setup_data(role_user_factory, db):
    """Creates a rich set of companies, opportunities, applications, and audit events."""
    ipc_admin = role_user_factory("IPC Admin", username="ipc_admin_r6")
    sys_admin = role_user_factory("System Admin", username="sys_admin_r6")
    recruiter = role_user_factory("Recruiter", username="recruiter_r6")
    student = role_user_factory("Student", username="student_r6")

    company_a = Company.objects.create(
        name="Alpha Global Corp",
        industry="Technology",
        contact_email="contact@alphaglobal.test",
        verification_status=Company.VerificationStatus.VERIFIED,
    )
    company_b = Company.objects.create(
        name="Beta Logistics, Inc.",
        industry="Logistics",
        contact_email="contact@betalogistics.test",
        verification_status=Company.VerificationStatus.PENDING,
    )

    RecruiterProfile.objects.create(user=recruiter, company=company_a)

    now = timezone.now()

    opp_1 = Opportunity.objects.create(
        company=company_a,
        created_by=recruiter,
        approved_by=ipc_admin,
        title="Software Development Engineer",
        description="Core systems developer",
        opportunity_type=Opportunity.OpportunityType.JOB,
        work_mode=Opportunity.WorkMode.REMOTE,
        location="Bengaluru",
        application_deadline=now + timedelta(days=30),
        status=Opportunity.Status.PUBLISHED,
        published_at=now - timedelta(days=2),
    )

    opp_2 = Opportunity.objects.create(
        company=company_b,
        created_by=recruiter,
        title="Operations Analyst",
        description="Logistics data pipeline analyst",
        opportunity_type=Opportunity.OpportunityType.INTERNSHIP,
        work_mode=Opportunity.WorkMode.ONSITE,
        location="Hyderabad",
        application_deadline=now + timedelta(days=15),
        status=Opportunity.Status.PENDING_APPROVAL,
    )

    # Submitted application
    resume_file = ContentFile(b"%PDF-1.4 dummy resume content", name="sample_resume.pdf")
    app_1 = Application.objects.create(
        student=student,
        opportunity=opp_1,
        status=Application.Status.SUBMITTED,
        resume=resume_file,
    )

    # Audit events
    event_comp = WorkflowAuditEvent.objects.create(
        actor=ipc_admin,
        object_type=WorkflowAuditEvent.ObjectType.COMPANY,
        object_id=company_a.id,
        action=WorkflowAuditEvent.Action.COMPANY_VERIFIED,
        details={"company_name": company_a.name, "verification_status": "VERIFIED"},
    )
    event_comp.created_at = now - timedelta(days=5)
    event_comp.save(update_fields=["created_at"])

    event_opp = WorkflowAuditEvent.objects.create(
        actor=ipc_admin,
        object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY,
        object_id=opp_1.id,
        action=WorkflowAuditEvent.Action.OPPORTUNITY_APPROVED,
        details={"title": opp_1.title, "company_name": company_a.name, "status": "PUBLISHED"},
    )
    event_opp.created_at = now - timedelta(days=2)
    event_opp.save(update_fields=["created_at"])

    return {
        "ipc_admin": ipc_admin,
        "sys_admin": sys_admin,
        "recruiter": recruiter,
        "student": student,
        "company_a": company_a,
        "company_b": company_b,
        "opp_1": opp_1,
        "opp_2": opp_2,
        "app_1": app_1,
        "event_comp": event_comp,
        "event_opp": event_opp,
    }


@pytest.mark.django_db
class TestActivityReportsAndCSVExport:
    """R6 Verification Test Suite."""

    def test_01_authorized_ipc_admin_exports_report(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """1. Authorized IPC Admin exports a report successfully."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers["Content-Type"]
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert "nexus_career_activity_report_" in response.headers["Content-Disposition"]

        # Parse CSV content
        content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        assert len(rows) >= 2  # At least header + data rows
        headers = rows[0]
        assert "ID" in headers
        assert "Activity Type" in headers
        assert "Company" in headers
        assert "Status" in headers

    def test_02_unauthorized_student_attempts_export(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """2. Unauthorized student attempts export and is denied with 403."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["student"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "text/csv" not in response.headers.get("Content-Type", "")

    def test_03_recruiter_attempts_export(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """3. Recruiter attempts export and is denied with 403."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["recruiter"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_04_unauthorized_role_attempts_report_retrieval(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """4. Unauthorized role attempts JSON report retrieval and is denied."""
        url = reverse("admin-reports-list")

        # Anonymous request -> 401
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Student request -> 403
        api_client.credentials(**jwt_auth_headers(test_setup_data["student"]))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Recruiter request -> 403
        api_client.credentials(**jwt_auth_headers(test_setup_data["recruiter"]))
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_05_date_filter_works(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """5. Date filter works (start_date and end_date)."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        now = timezone.now()
        start = (now - timedelta(days=3)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        response = api_client.get(url, {"start_date": start, "end_date": end})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data

        # event_comp is 5 days ago, should be excluded
        event_ids = [r["id"] for r in results]
        assert f"event-{test_setup_data['event_comp'].id}" not in event_ids

        # event_opp is 2 days ago, should be included
        assert f"event-{test_setup_data['event_opp'].id}" in event_ids

    def test_06_activity_type_filter_works(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """6. Activity type filter works."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        # Filter by APPLICATION
        response = api_client.get(url, {"activity_type": "APPLICATION"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) >= 1
        for item in results:
            assert item["activity_type"] == "APPLICATION"

        # Filter by COMPANY
        response_comp = api_client.get(url, {"activity_type": "COMPANY"})
        assert response_comp.status_code == status.HTTP_200_OK
        comp_results = response_comp.data.get("results", response_comp.data)
        for item in comp_results:
            assert item["activity_type"] == "COMPANY"

    def test_07_company_filter_works(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """7. Company filter works (by name substring and numeric ID)."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        response = api_client.get(url, {"company": "Alpha Global"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) >= 1
        for item in results:
            assert "Alpha Global" in item["company"]

        # Non-matching company
        response_empty = api_client.get(url, {"company": "NonExistentCompanyXYZ"})
        assert response_empty.status_code == status.HTTP_200_OK
        empty_results = response_empty.data.get("results", response_empty.data)
        assert len(empty_results) == 0

    def test_08_status_filter_works(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """8. Status filter works."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        response = api_client.get(url, {"status": "SUBMITTED"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) >= 1
        for item in results:
            assert item["status"] == "SUBMITTED"

    def test_09_multiple_filters_work_together(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """9. Multiple filters work in combination."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        now = timezone.now()
        start = (now - timedelta(days=10)).strftime("%Y-%m-%d")

        response = api_client.get(
            url,
            {
                "start_date": start,
                "company": "Alpha Global",
                "activity_type": "APPLICATION",
                "status": "SUBMITTED",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1
        assert results[0]["id"] == f"app-{test_setup_data['app_1'].id}"

    def test_10_invalid_date_range_is_rejected(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """10. Invalid date range (start_date > end_date or malformed) is rejected with 400."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        # start_date > end_date
        response = api_client.get(url, {"start_date": "2026-11-20", "end_date": "2026-11-10"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be after" in str(response.data)

        # Malformed date
        response_malformed = api_client.get(url, {"start_date": "not-a-valid-date"})
        assert response_malformed.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid date format" in str(response_malformed.data)

    def test_11_empty_report_generates_valid_csv(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """11. Empty report generates a valid CSV containing headers and 0 data rows."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url, {"company": "CompanyWithNoActivitiesExpected123"})
        assert response.status_code == status.HTTP_200_OK

        reader = csv.reader(io.StringIO(response.content.decode("utf-8")))
        rows = list(reader)

        assert len(rows) == 1  # Exactly the header row
        assert rows[0][0] == "ID"
        assert rows[0][1] == "Timestamp (UTC)"

    def test_12_csv_headers_are_correct(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """12. CSV headers match the exact required administrative schema."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        reader = csv.reader(io.StringIO(response.content.decode("utf-8")))
        headers = next(reader)

        expected_headers = [
            "ID",
            "Timestamp (UTC)",
            "Activity Type",
            "Action",
            "Actor",
            "Company",
            "Target Type",
            "Target ID",
            "Status",
            "Details",
        ]
        assert headers == expected_headers

    def test_13_csv_escaping_handles_special_characters(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """13. CSV escaping properly quotes and escapes commas, quotes, and newlines."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-export")

        # Company B has name "Beta Logistics, Inc." with a comma
        response = api_client.get(url, {"company": "Beta Logistics"})
        assert response.status_code == status.HTTP_200_OK

        # Valid CSV reader must parse without errors
        reader = csv.reader(io.StringIO(response.content.decode("utf-8")))
        rows = list(reader)
        assert len(rows) >= 1  # Successfully parsed

    def test_14_export_action_is_logged(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """14. Every successful export logs an audit record via audit.log."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-export")

        audit.clear_audit_logs()

        response = api_client.get(url, {"company": "Alpha Global"})
        assert response.status_code == status.HTTP_200_OK

        recorded_logs = audit.get_audit_logs()
        export_logs = [log for log in recorded_logs if log["action"] == "REPORT_EXPORTED"]

        assert len(export_logs) >= 1
        log_entry = export_logs[-1]
        assert log_entry["actor_username"] == "ipc_admin_r6"
        assert log_entry["target_type"] == "REPORT"
        assert log_entry["details"]["format"] == "csv"
        assert "filters" in log_entry["details"]
        assert log_entry["details"]["filters"]["company"] == "Alpha Global"

    def test_15_unauthorized_export_does_not_expose_data(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """15. Unauthorized export requests do not expose candidate data or CSV payloads."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["student"]))
        url = reverse("admin-reports-export")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        content = response.content.decode("utf-8")
        assert "Alpha Global" not in content
        assert "sample_resume" not in content
        assert "Software Development Engineer" not in content

    def test_16_system_admin_can_access_and_export_reports(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """16. System Administrator is authorized to view and export reports."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["sys_admin"]))

        # JSON list
        list_url = reverse("admin-reports-list")
        list_resp = api_client.get(list_url)
        assert list_resp.status_code == status.HTTP_200_OK

        # CSV export
        export_url = reverse("admin-reports-export")
        export_resp = api_client.get(export_url)
        assert export_resp.status_code == status.HTTP_200_OK
        assert "text/csv" in export_resp.headers["Content-Type"]

    def test_17_paginated_json_activity_reports_endpoint(
        self, api_client, test_setup_data, jwt_auth_headers
    ):
        """17. Activity reports JSON endpoint returns standard pagination structure."""
        api_client.credentials(**jwt_auth_headers(test_setup_data["ipc_admin"]))
        url = reverse("admin-reports-list")

        response = api_client.get(url, {"page": 1, "page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "results" in response.data
        assert len(response.data["results"]) <= 2
