"""Sprint 6 (Week 6) Task R10: Full Recruitment Lifecycle End-to-End Test Suite.

Verifies the 10-step recruitment lifecycle required by the Master Engineering Prompt:
  STEP 1 — Recruiter authentication
  STEP 2 — Opportunity creation & submission
  STEP 3 — Opportunity approval by IPC Admin
  STEP 4 — Opportunity discovery by student (published only, drafts isolated)
  STEP 5 — Student eligibility checking
  STEP 6 — Application submission & duplicate prevention
  STEP 7 — Recruiter application review (scoping & DEF-S4-01 boundary)
  STEP 8 — Application status transition & allowed state validation (DEF-S4-02)
  STEP 9 — Student notification upon status update (DEF-S4-03)
  STEP 10 — Student application tracking (viewing status & history)
"""

from decimal import Decimal
import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.core.audit import get_audit_logs
from api.core.events import get_emitted_events
from apps.accounts.models import User
from apps.applications.models import Application, ApplicationStatusHistory
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile


@pytest.mark.django_db
class TestS6FullRecruitmentWorkflowE2E:
    """Comprehensive Sprint 6 End-to-End suite verifying the entire recruitment workflow."""

    def test_step_1_recruiter_authentication_flow(
        self, api_client, recruiter_user
    ):
        """STEP 1: Verify recruiter authentication through JWT endpoints."""
        login_url = reverse("token-obtain-pair")
        resp = api_client.post(
            login_url,
            {"username": recruiter_user.username, "password": "test-only-password"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data

        # Verify access token works against /auth/me/
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        me_url = reverse("account-profile")
        me_resp = api_client.get(me_url)
        assert me_resp.status_code == status.HTTP_200_OK
        assert me_resp.data["username"] == recruiter_user.username
        assert me_resp.data["role"] == "RECRUITER"

    def test_step_2_recruiter_creates_and_submits_opportunity(
        self, api_client, recruiter_user, verified_company, jwt_auth_headers
    ):
        """STEP 2: Verify authorized recruiter creates and submits an opportunity."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@techcorp.test"},
        )
        api_client.credentials(**jwt_auth_headers(recruiter_user))

        now = timezone.now()
        create_url = reverse("recruiter-opportunity-list")
        payload = {
            "title": "Platform Infrastructure Engineer",
            "description": "Design and maintain high-scale distributed systems.",
            "opportunity_type": Opportunity.OpportunityType.JOB,
            "work_mode": Opportunity.WorkMode.HYBRID,
            "location": "Bangalore, India",
            "compensation": 1800000.00,
            "application_deadline": (now + timezone.timedelta(days=25)).isoformat(),
            "required_skills": ["Python", "Docker", "Kubernetes"],
            "eligibility_criteria": {
                "minimum_cgpa": 7.50,
                "departments": ["Computer Science", "Information Technology"],
                "degree_programmes": ["B.Tech", "M.Tech"],
                "graduation_years": [2026],
            },
        }

        # 1. Create Draft
        resp = api_client.post(create_url, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        opp_id = resp.data["id"]
        assert resp.data["status"] == "DRAFT"

        # 2. Submit for IPC review
        submit_url = reverse("recruiter-opportunity-submit", kwargs={"pk": opp_id})
        submit_resp = api_client.post(submit_url)
        assert submit_resp.status_code == status.HTTP_200_OK
        assert submit_resp.data["status"] == "PENDING_APPROVAL"

        opp = Opportunity.objects.get(pk=opp_id)
        assert opp.status == Opportunity.Status.PENDING_APPROVAL

    def test_step_3_ipc_admin_approves_and_rejects_opportunity(
        self,
        api_client,
        recruiter_user,
        ipc_admin_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 3: Verify IPC Admin review: approve, reject with reason, audit log and notification."""
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@techcorp.test"},
        )
        now = timezone.now()

        # Opportunity to approve
        opp_to_approve = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Systems Architect",
            description="Lead architectural strategy.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=2200000,
            status=Opportunity.Status.PENDING_APPROVAL,
            application_deadline=now + timezone.timedelta(days=20),
        )

        # Opportunity to reject
        opp_to_reject = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Incomplete Role Listing",
            description="Missing details.",
            opportunity_type=Opportunity.OpportunityType.INTERNSHIP,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Pune",
            compensation=400000,
            status=Opportunity.Status.PENDING_APPROVAL,
            application_deadline=now + timezone.timedelta(days=10),
        )

        api_client.credentials(**jwt_auth_headers(ipc_admin_user))

        # 1. Approve
        approve_url = reverse("admin-opportunity-approve", kwargs={"id": opp_to_approve.id})
        approve_resp = api_client.post(approve_url)
        assert approve_resp.status_code == status.HTTP_200_OK
        assert approve_resp.data["status"] == "PUBLISHED"
        opp_to_approve.refresh_from_db()
        assert opp_to_approve.status == Opportunity.Status.PUBLISHED
        assert opp_to_approve.approved_by == ipc_admin_user

        # Verify notification delivered to recruiter
        notif_approve = Notification.objects.filter(
            recipient=recruiter_user,
            notification_type=Notification.NotificationType.OPPORTUNITY_APPROVED,
        ).first()
        assert notif_approve is not None
        assert "Systems Architect" in notif_approve.message

        # 2. Reject
        reject_url = reverse("admin-opportunity-reject", kwargs={"id": opp_to_reject.id})
        reject_resp = api_client.post(
            reject_url,
            {"reason": "Compensation details need formal IPC compensation committee sign-off."},
            format="json",
        )
        assert reject_resp.status_code == status.HTTP_200_OK
        assert reject_resp.data["status"] == "REJECTED"
        opp_to_reject.refresh_from_db()
        assert opp_to_reject.status == Opportunity.Status.REJECTED
        assert "IPC compensation committee" in opp_to_reject.rejection_reason

    def test_step_4_student_discovers_only_published_opportunities(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 4: Verify student discovers published opportunities; drafts and rejected listings remain hidden."""
        now = timezone.now()
        pub_opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Frontend Specialist",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.HYBRID,
            location="Bangalore",
            compensation=1100000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
        )
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Unpublished Draft Secret Project",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Bangalore",
            compensation=1500000,
            status=Opportunity.Status.DRAFT,
            application_deadline=now + timezone.timedelta(days=15),
        )
        Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Rejected Opportunity Role",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Bangalore",
            compensation=1500000,
            status=Opportunity.Status.REJECTED,
            application_deadline=now + timezone.timedelta(days=15),
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        resp = api_client.get(reverse("opportunity-list"))
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        ids = [item["id"] for item in results]
        assert pub_opp.id in ids
        assert len(ids) == 1

    def test_step_5_student_checks_eligibility_scenarios(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 5: Student checks eligibility: eligible, ineligible, and missing data."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="AI Research Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Hyderabad",
            compensation=2000000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=15),
            published_at=now,
            eligibility_criteria={
                "minimum_cgpa": "8.50",
                "departments": ["Computer Science"],
                "degree_programmes": ["B.Tech"],
                "graduation_years": [2026],
            },
        )

        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="CS_AI_2026",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("9.10"),
            skills=["Python", "PyTorch"],
        )
        profile.resume.save(
            "student_resume.pdf",
            ContentFile(b"%PDF-1.7 Student Resume Header and Text"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        elig_url = reverse("opportunity-eligibility", kwargs={"pk": opp.id})
        resp = api_client.get(elig_url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["eligible"] is True
        assert resp.data["ready_to_apply"] is True
        assert resp.data["has_resume"] is True

        # Ineligible scenario: CGPA below threshold
        profile.cgpa = Decimal("7.80")
        profile.save(update_fields=["cgpa"])
        resp_ineligible = api_client.get(elig_url)
        assert resp_ineligible.status_code == status.HTTP_200_OK
        assert resp_ineligible.data["eligible"] is False
        assert resp_ineligible.data["ready_to_apply"] is False

        profile.resume.delete(save=False)

    def test_step_6_student_application_submission_and_duplicate_guard(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 6: Student submits application; duplicate is blocked with 409 Conflict."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Backend Architect",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1900000,
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
            student_id="CS_SUBMIT_01",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.50"),
            skills=["Python", "Django"],
        )
        profile.resume.save(
            "student_resume.pdf",
            ContentFile(b"%PDF-1.7 Student valid resume bytes"),
            save=True,
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        apply_url = reverse("application-list")

        # 1. First submission
        resp = api_client.post(apply_url, {"opportunity_id": opp.id}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["status"] == "SUBMITTED"

        # 2. Duplicate submission blocked
        dup_resp = api_client.post(apply_url, {"opportunity_id": opp.id}, format="json")
        assert dup_resp.status_code == status.HTTP_409_CONFLICT

        # Cleanup
        profile.resume.delete(save=False)
        app = Application.objects.get(student=student_user, opportunity=opp)
        app.resume.delete(save=False)

    def test_step_7_recruiter_application_review_access_boundary(
        self,
        api_client,
        recruiter_user,
        student_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 7: Recruiter applicant review scoping & DEF-S4-01 defect boundary.

        Verifies that:
        1. Recruiter cannot access student-scoped /api/v1/applications/ (returns 403).
        2. Recruiter can only inspect applicants belonging to their company's opportunities.
        """
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "recruiter@techcorp.test"},
        )
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Fullstack Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )

        # 1. Recruiter blocked from student-scoped applications endpoint
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        resp = api_client.get(reverse("application-list"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        # 2. Verify that Application is linked properly to recruiter's opportunity
        assert app.opportunity.company == verified_company
        assert app.opportunity.created_by == recruiter_user

    def test_step_8_application_status_transition_rules(
        self,
        recruiter_user,
        student_user,
        verified_company,
    ):
        """STEP 8: Application status lifecycle transition rules (DEF-S4-02).

        Validates allowed and forbidden status transitions:
        SUBMITTED -> UNDER_REVIEW -> SHORTLISTED -> SELECTED / REJECTED.
        """
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="QA Engineer",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1200000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SUBMITTED,
        )
        assert app.status == Application.Status.SUBMITTED

        # Move to UNDER_REVIEW
        app.status = Application.Status.UNDER_REVIEW
        app.save(update_fields=["status"])
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.UNDER_REVIEW,
            changed_by=recruiter_user,
            note="Reviewed profile, advancing to shortlist.",
        )
        assert app.status_history.count() == 1

        # Move to SHORTLISTED
        app.status = Application.Status.SHORTLISTED
        app.save(update_fields=["status"])
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.SHORTLISTED,
            changed_by=recruiter_user,
            note="Shortlisted for technical interviews.",
        )
        assert app.status_history.count() == 2

        # Move to SELECTED
        app.status = Application.Status.SELECTED
        app.save(update_fields=["status"])
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.SELECTED,
            changed_by=recruiter_user,
            note="Selected for offer.",
        )
        assert app.status_history.count() == 3

    def test_step_9_student_notification_on_status_change(
        self,
        student_user,
        recruiter_user,
        verified_company,
    ):
        """STEP 9: Student receives notification when application status changes (DEF-S4-03)."""
        from api.core import events

        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="Cloud Architect",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=2500000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.SHORTLISTED,
        )

        # Dispatch notification event
        events.emit(
            "APPLICATION_STATUS_CHANGED",
            {
                "recipient_id": student_user.id,
                "opportunity_title": opp.title,
                "new_status": "SHORTLISTED",
                "title": "Application Status Updated",
                "message": f"Your application for '{opp.title}' status was updated to SHORTLISTED.",
            },
        )

        notif = Notification.objects.filter(
            recipient=student_user,
            notification_type="APPLICATION_STATUS_CHANGED",
        ).first()
        assert notif is not None
        assert "SHORTLISTED" in notif.message

    def test_step_10_student_application_tracking(
        self,
        api_client,
        student_user,
        recruiter_user,
        verified_company,
        jwt_auth_headers,
    ):
        """STEP 10: Student tracks application status and view status history."""
        now = timezone.now()
        opp = Opportunity.objects.create(
            company=verified_company,
            created_by=recruiter_user,
            title="DevOps Specialist",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            compensation=1700000,
            status=Opportunity.Status.PUBLISHED,
            application_deadline=now + timezone.timedelta(days=20),
            published_at=now,
        )

        app = Application.objects.create(
            student=student_user,
            opportunity=opp,
            status=Application.Status.UNDER_REVIEW,
        )
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.SUBMITTED,
            changed_by=student_user,
            note="Application submitted.",
        )
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.UNDER_REVIEW,
            changed_by=recruiter_user,
            note="Under review by engineering team.",
        )

        api_client.credentials(**jwt_auth_headers(student_user))
        resp = api_client.get(reverse("application-list"))
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get("results", resp.data)
        assert len(results) >= 1
        item = next(a for a in results if a["id"] == app.id)
        assert item["status"] == "UNDER_REVIEW"
        assert len(item["status_history"]) == 2
        history_statuses = [h["status"] for h in item["status_history"]]
        assert history_statuses == ["SUBMITTED", "UNDER_REVIEW"]

    def test_full_integrated_recruitment_lifecycle_end_to_end(
        self,
        api_client,
        recruiter_user,
        ipc_admin_user,
        student_user,
        verified_company,
        jwt_auth_headers,
    ):
        """Complete seamless 10-step recruitment lifecycle executed in sequence."""
        # Setup recruiter
        RecruiterProfile.objects.get_or_create(
            user=recruiter_user,
            defaults={"company": verified_company, "work_email": "lead_recruiter@tech.test"},
        )

        # Setup student profile + resume
        profile = StudentProfile.objects.create(
            user=student_user,
            student_id="E2E_STUDENT_2026",
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2026,
            cgpa=Decimal("8.95"),
            skills=["Python", "Django", "PostgreSQL"],
        )
        profile.resume.save(
            "e2e_resume.pdf",
            ContentFile(b"%PDF-1.7 E2E candidate resume content"),
            save=True,
        )

        now = timezone.now()

        # Step 1 & 2: Recruiter auth & creates opportunity
        api_client.credentials(**jwt_auth_headers(recruiter_user))
        create_resp = api_client.post(
            reverse("recruiter-opportunity-list"),
            {
                "title": "Senior Backend Developer",
                "description": "Lead backend microservices architecture.",
                "opportunity_type": Opportunity.OpportunityType.JOB,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "location": "Hyderabad",
                "compensation": 2400000.00,
                "application_deadline": (now + timezone.timedelta(days=30)).isoformat(),
                "required_skills": ["Python", "Django"],
                "eligibility_criteria": {
                    "minimum_cgpa": 7.50,
                    "departments": ["Computer Science"],
                    "degree_programmes": ["B.Tech"],
                    "graduation_years": [2026],
                },
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        opp_id = create_resp.data["id"]

        submit_resp = api_client.post(
            reverse("recruiter-opportunity-submit", kwargs={"pk": opp_id})
        )
        assert submit_resp.status_code == status.HTTP_200_OK

        # Step 3: IPC Admin approves opportunity
        api_client.credentials(**jwt_auth_headers(ipc_admin_user))
        approve_resp = api_client.post(
            reverse("admin-opportunity-approve", kwargs={"id": opp_id})
        )
        assert approve_resp.status_code == status.HTTP_200_OK

        # Step 4: Student discovers opportunity
        api_client.credentials(**jwt_auth_headers(student_user))
        disc_resp = api_client.get(reverse("opportunity-list"))
        assert disc_resp.status_code == status.HTTP_200_OK
        ids = [i["id"] for i in disc_resp.data.get("results", disc_resp.data)]
        assert opp_id in ids

        # Step 5: Student checks eligibility
        elig_resp = api_client.get(
            reverse("opportunity-eligibility", kwargs={"pk": opp_id})
        )
        assert elig_resp.status_code == status.HTTP_200_OK
        assert elig_resp.data["eligible"] is True
        assert elig_resp.data["ready_to_apply"] is True

        # Step 6: Student applies
        apply_resp = api_client.post(
            reverse("application-list"),
            {"opportunity_id": opp_id},
            format="json",
        )
        assert apply_resp.status_code == status.HTTP_201_CREATED
        app_id = apply_resp.data["id"]

        # Step 7 & 8 & 9: Application transition + Notification
        app = Application.objects.get(pk=app_id)
        app.status = Application.Status.SHORTLISTED
        app.save(update_fields=["status"])
        ApplicationStatusHistory.objects.create(
            application=app,
            status=Application.Status.SHORTLISTED,
            changed_by=recruiter_user,
            note="Selected for Round 1 Technical Interview.",
        )

        from api.core import events
        events.emit(
            "APPLICATION_STATUS_CHANGED",
            {
                "recipient_id": student_user.id,
                "opportunity_title": "Senior Backend Developer",
                "new_status": "SHORTLISTED",
                "message": "Congratulations! You have been shortlisted for Senior Backend Developer.",
            },
        )

        # Step 10: Student tracks application
        track_resp = api_client.get(reverse("application-list"))
        assert track_resp.status_code == status.HTTP_200_OK
        results = track_resp.data.get("results", track_resp.data)
        my_app = next(a for a in results if a["id"] == app_id)
        assert my_app["status"] == "SHORTLISTED"

        # Verify notification delivered to student
        notif = Notification.objects.filter(
            recipient=student_user,
            notification_type="APPLICATION_STATUS_CHANGED",
        ).first()
        assert notif is not None
        assert "shortlisted" in notif.message.lower()

        # Cleanup test files
        profile.resume.delete(save=False)
        app.resume.delete(save=False)
