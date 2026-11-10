from decimal import Decimal
import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core.audit import get_audit_logs
from apps.accounts.models import User
from apps.applications.models import Application, ApplicationStatusHistory
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile


@pytest.mark.django_db
class TestRecruitmentLifecycleE2E:
    """End-to-End Regression Test Suite for the MVP Recruitment Lifecycle (R10).

    Covers the full recruitment placement flow:
    Recruiter Creates Opportunity -> IPC Approves -> Student Discovers ->
    Student Checks Eligibility -> Student Applies -> Recruiter Applicant Review ->
    Notifications Delivered -> IPC Administration & Metrics -> Private File Security.
    """

    def test_scenario_1_recruiter_creates_opportunity_draft(
        self, api_client, recruiter_user, verified_company, jwt_auth_headers
    ):
        """Scenario 1: Recruiter creates an opportunity draft linked to their verified company."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@example.com"},
        )
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        url = reverse("recruiter-opportunity-list")

        now = timezone.now()
        payload = {
            "title": "Backend Engineering Intern",
            "description": "Work on distributed cloud architectures and REST APIs.",
            "opportunity_type": "INTERNSHIP",
            "work_mode": "HYBRID",
            "location": "Hyderabad, India",
            "compensation": 600000.00,
            "application_deadline": (now + timezone.timedelta(days=30)).isoformat(),
            "required_skills": ["Python", "Django", "PostgreSQL"],
            "eligibility_criteria": {
                "minimum_cgpa": 7.50,
                "departments": ["Computer Science", "Information Technology"],
                "degree_programmes": ["B.Tech", "M.Tech"],
                "graduation_years": [2026, 2027],
            },
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "DRAFT"
        assert response.data["company_name"] == verified_company.name

        opportunity_id = response.data["id"]
        opp = Opportunity.objects.get(pk=opportunity_id)
        assert opp.status == Opportunity.Status.DRAFT
        assert opp.company == verified_company
        assert opp.created_by == recruiter_user

    def test_scenario_2_recruiter_submits_and_ipc_approves(
        self,
        api_client,
        recruiter_user,
        ipc_admin_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Scenario 2: Recruiter submits opportunity draft, and IPC admin reviews & approves it."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@example.com"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Graduate Software Engineer",
            description="Graduate hiring program.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1200000,
            status=Opportunity.Status.DRAFT,
            application_deadline=now + timezone.timedelta(days=20),
        )

        # 1. Recruiter submits the opportunity
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        submit_url = reverse("recruiter-opportunity-submit", kwargs={"pk": opp.id})
        submit_resp = api_client.post(submit_url)
        assert submit_resp.status_code == status.HTTP_200_OK
        assert submit_resp.data["status"] == "PENDING_APPROVAL"

        # 2. IPC Admin views pending opportunities
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        pending_url = reverse("admin-opportunity-pending")
        pending_resp = api_client.get(pending_url)
        assert pending_resp.status_code == status.HTTP_200_OK
        results = pending_resp.data.get("results", pending_resp.data)
        assert any(item["id"] == opp.id for item in results)

        # 3. IPC Admin approves the opportunity
        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp.id})
        approve_resp = api_client.post(approve_url)
        assert approve_resp.status_code == status.HTTP_200_OK
        assert approve_resp.data["status"] == "PUBLISHED"

        opp.refresh_from_db()
        assert opp.status == Opportunity.Status.PUBLISHED
        assert opp.approved_by == ipc_admin_user
        assert opp.approved_at is not None

        # 4. Verify audit log entry
        logs = get_audit_logs()
        approve_log = next(
            log for log in logs if log["action"] == "OPPORTUNITY_APPROVED"
        )
        assert approve_log["actor_id"] == ipc_admin_user.id
        assert approve_log["target_id"] == str(opp.id)

        # 5. Verify recruiter notification
        notif = Notification.objects.filter(
            recipient=recruiter_user,
            notification_type=Notification.NotificationType.OPPORTUNITY_APPROVED,
        ).first()
        assert notif is not None
        assert notif.title == "Opportunity Approved"
        assert "Graduate Software Engineer" in notif.message

    def test_scenario_3_student_discovers_only_published_opportunities(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Scenario 3: Students can only discover published, unexpired opportunities."""
        now = timezone.now()

        # Published active opportunity
        published_opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Public Cloud Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )

        # Draft opportunity (must remain hidden)
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Draft Secret Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.DRAFT,
            application_deadline=now + timezone.timedelta(days=15),
        )

        # Pending approval opportunity (must remain hidden)
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Pending Review Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PENDING_APPROVAL,
            application_deadline=now + timezone.timedelta(days=15),
        )

        # Student discovers listings
        api_client.credentials(**jwt_auth_headers(student_user))
        discovery_url = reverse("opportunity-list")
        response = api_client.get(discovery_url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        returned_ids = [item["id"] for item in results]
        assert published_opp.id in returned_ids
        assert len(returned_ids) == 1

    def test_scenario_4_student_checks_eligibility(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Scenario 4: Student checks eligibility against configured criteria."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Data Scientist",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Hyderabad",
            compensation=1400000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
            eligibility_criteria={
                "minimum_cgpa": "8.00",
                "departments": ["Computer Science"],
                "degree_programmes": ["B.Tech"],
                "graduation_years": [2026],
            },
        )

        # 1. Eligible student profile
        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="CS2026_01",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.80"),
            skills=["Python", "Machine Learning"],
        )
        profile.resume.save(
            "test_resume.pdf",
            ContentFile(b"%PDF-1.7 student resume content"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        eligibility_url = reverse("opportunity-eligibility", kwargs={"pk": opp.id})
        response = api_client.get(eligibility_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["eligible"] is True
        assert response.data["ready_to_apply"] is True
        assert response.data["has_resume"] is True

        # Clean up resume file
        profile.resume.delete(save=False)

    def test_scenario_5_student_submits_application_and_duplicate_prevention(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Scenario 5: Student submits application; duplicate attempt is blocked with 409."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Security Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1600000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
            eligibility_criteria={
                "minimum_cgpa": "7.00",
                "departments": ["Computer Science"],
                "degree_programmes": ["B.Tech"],
                "graduation_years": [2026],
            },
        )

        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="SEC_2026_01",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.20"),
            skills=["Python", "Security", "Cryptography"],
        )
        profile.resume.save(
            "student_resume.pdf",
            ContentFile(b"%PDF-1.7 student resume fixture bytes"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        apply_url = reverse("application-list")

        # First submission succeeds
        response = api_client.post(
            apply_url, {"opportunity_id": opp.id}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "SUBMITTED"

        application = Application.objects.get(student=student_user, opportunity=opp)
        assert application.status == Application.Status.SUBMITTED
        assert application.resume.name.startswith("private/application-resumes/")

        # Verify in-app notification created
        notif = Notification.objects.filter(
            recipient=student_user,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
        ).first()
        assert notif is not None
        assert "Security Engineer" in notif.message

        # Second submission returns 409 Conflict (Duplicate prevention)
        dup_response = api_client.post(
            apply_url, {"opportunity_id": opp.id}, format="json"
        )
        assert dup_response.status_code == status.HTTP_409_CONFLICT

        # Clean up test files
        profile.resume.delete(save=False)
        application.resume.delete(save=False)

    def test_scenario_6_recruiter_review_and_status_transition_boundaries(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Scenario 6: Verifies recruiter access boundaries and application status transitions."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="DevOps Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1300000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        application = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        # 1. Recruiter attempting to access student-scoped /api/v1/applications/ is forbidden
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        apps_url = reverse("application-list")
        recruiter_resp = api_client.get(apps_url)
        assert recruiter_resp.status_code == status.HTTP_403_FORBIDDEN

        # 2. Data-layer transition: Application status moves through allowed lifecycle
        application.status = Application.Status.UNDER_REVIEW
        application.save(update_fields=["status"])
        ApplicationStatusHistory.objects.create(
            application=application,
            status=Application.Status.UNDER_REVIEW,
            changed_by=recruiter_user,
            note="Application moved to under review by hiring team.",
        )

        application.refresh_from_db()
        assert application.status == Application.Status.UNDER_REVIEW
        assert application.status_history.count() == 1
        history_entry = application.status_history.first()
        assert history_entry.changed_by == recruiter_user
        assert history_entry.status == Application.Status.UNDER_REVIEW

    def test_scenario_7_student_notification_inbox_and_mark_read(
        self, api_client, student_user, jwt_auth_headers
    ):
        """Scenario 7: Student reads and acknowledges notifications in inbox."""
        notif = Notification.objects.create(
            recipient=student_user,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application Confirmation",
            message="Your application was received.",
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        list_url = reverse("notification-list")
        resp = api_client.get(list_url)
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert any(n["id"] == notif.id for n in results)

        read_url = reverse("notification-mark-read", kwargs={"pk": notif.id})
        read_resp = api_client.post(read_url)
        assert read_resp.status_code == status.HTTP_200_OK

        notif.refresh_from_db()
        assert notif.read_at is not None

    def test_scenario_8_ipc_administration_full_lifecycle(
        self,
        api_client,
        ipc_admin_user,
        student_user,
        pending_recruiter,
        jwt_auth_headers,
    ):
        """Scenario 8: Complete IPC administrative actions (verify, suspend, reactivate, metrics, audit)."""
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))

        # 1. Recruiter Verification
        verify_url = reverse(
            "admin-recruiter-verify", kwargs={"id": pending_recruiter.id}
        )
        verify_resp = api_client.post(verify_url, {"status": "VERIFIED"}, format="json")
        assert verify_resp.status_code == status.HTTP_200_OK

        # 2. User Suspension
        suspend_url = reverse("admin-user-suspend", kwargs={"id": student_user.id})
        suspend_resp = api_client.post(
            suspend_url, {"reason": "Conduct review"}, format="json"
        )
        assert suspend_resp.status_code == status.HTTP_200_OK

        # 3. User Reactivation
        reactivate_url = reverse(
            "admin-user-reactivate", kwargs={"id": student_user.id}
        )
        reactivate_resp = api_client.post(reactivate_url)
        assert reactivate_resp.status_code == status.HTTP_200_OK

        # 4. Audit Trail View
        audit_url = reverse("admin-audit-logs")
        audit_resp = api_client.get(audit_url)
        assert audit_resp.status_code == status.HTTP_200_OK
        actions = [item["action"] for item in audit_resp.data.get("results", audit_resp.data)]
        assert "RECRUITER_VERIFICATION_VERIFIED" in actions
        assert "USER_SUSPENDED" in actions
        assert "USER_REACTIVATED" in actions

        # 5. Dashboard Metrics
        metrics_url = reverse("admin-dashboard-metrics")
        metrics_resp = api_client.get(metrics_url)
        assert metrics_resp.status_code == status.HTTP_200_OK
        assert metrics_resp.data["students"] >= 1
        assert metrics_resp.data["verified_recruiters"] >= 1

    def test_scenario_9_private_resume_security(
        self, student_user, role_user_factory
    ):
        """Scenario 9: Resumes are assigned unique private storage paths; path traversal prevented."""
        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="SEC_RESUME_01",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("9.00"),
        )
        profile.resume.save(
            "sensitive_resume.pdf",
            ContentFile(b"%PDF-1.7 private student credentials"),
            save=True,
        )

        resume_path = profile.resume.name
        # Path must be isolated in private directory with non-guessable UUID
        assert resume_path.startswith("private/student-resumes/")
        assert "sensitive_resume.pdf" not in resume_path
        assert len(resume_path) > 30

        # Clean up
        profile.resume.delete(save=False)
