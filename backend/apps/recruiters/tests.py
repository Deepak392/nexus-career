from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.opportunities.models import Opportunity
from .models import Company, RecruiterProfile, WorkflowAuditEvent

User = get_user_model()


class RecruiterCompanyAPITests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="recruiter-one", email="recruiter-one@example.com",
            password="StrongPass123!secure", role=User.Role.RECRUITER,
        )
        self.ipc_admin = User.objects.create_user(
            username="ipc-admin", email="ipc-admin@example.com",
            password="StrongPass123!secure", role=User.Role.IPC_ADMIN,
        )
        self.student = User.objects.create_user(
            username="student-one", email="student-one@example.com",
            password="StrongPass123!secure", role=User.Role.STUDENT,
        )
        self.url = reverse("recruiter-company-profile")
        self.data = {
            "name": "Northstar Technologies",
            "website": "https://northstar.example.com",
            "industry": "Technology",
            "contact_email": "careers@northstar.example.com",
            "contact_phone": "+91-9876543210",
            "description": "Software engineering and technology services.",
        }

    def test_anonymous_user_cannot_create_company(self):
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_company(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_can_create_pending_company_profile(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        company = Company.objects.get(name=self.data["name"])
        self.assertEqual(company.verification_status, Company.VerificationStatus.PENDING)
        self.assertTrue(RecruiterProfile.objects.filter(
            user=self.recruiter, company=company
        ).exists())
        self.assertTrue(WorkflowAuditEvent.objects.filter(
            actor=self.recruiter,
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=company.pk,
            action=WorkflowAuditEvent.Action.COMPANY_CREATED,
        ).exists())

    def test_recruiter_cannot_create_second_company_profile(self):
        company = Company.objects.create(
            name="Existing Co", industry="Technology",
            contact_email="contact@existing.example.com",
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=company)
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recruiter_can_read_own_company_profile(self):
        company = Company.objects.create(
            name="Northstar Technologies", industry="Technology",
            contact_email="careers@northstar.example.com",
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=company)
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], company.pk)

    def test_company_edit_resets_verification_to_pending(self):
        company = Company.objects.create(
            name="Northstar Technologies", industry="Technology",
            contact_email="careers@northstar.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=company)
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.patch(
            self.url, {"contact_phone": "+91-9000000000"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.verification_status, Company.VerificationStatus.PENDING)

    def test_company_edit_returns_published_and_pending_opportunities_to_draft(self):
        company = Company.objects.create(
            name="Northstar Technologies",
            industry="Technology",
            contact_email="careers@northstar.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=company)
        published = Opportunity.objects.create(
            company=company,
            created_by=self.recruiter,
            title="Published listing",
            description="A published listing with enough descriptive detail.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            application_deadline=timezone.now() + timedelta(days=20),
            status=Opportunity.Status.PUBLISHED,
            published_at=timezone.now(),
            approved_by=self.ipc_admin,
            approved_at=timezone.now(),
        )
        pending = Opportunity.objects.create(
            company=company,
            created_by=self.recruiter,
            title="Pending listing",
            description="A pending listing with enough descriptive detail.",
            opportunity_type=Opportunity.OpportunityType.INTERNSHIP,
            work_mode=Opportunity.WorkMode.HYBRID,
            location="Chennai",
            application_deadline=timezone.now() + timedelta(days=20),
            status=Opportunity.Status.PENDING_APPROVAL,
        )

        self.client.force_authenticate(user=self.recruiter)
        response = self.client.patch(
            self.url,
            {"contact_phone": "+91-9000000000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        published.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(published.status, Opportunity.Status.DRAFT)
        self.assertEqual(pending.status, Opportunity.Status.DRAFT)
        self.assertIsNone(published.approved_by)
        self.assertIsNone(published.approved_at)
        self.assertIsNone(published.published_at)
        audit = WorkflowAuditEvent.objects.get(
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=company.pk,
            action=WorkflowAuditEvent.Action.COMPANY_PROFILE_UPDATED,
        )
        self.assertEqual(audit.details["opportunities_returned_to_draft"], 2)

    def test_ipc_admin_can_verify_company(self):
        company = Company.objects.create(
            name="Northstar Technologies", industry="Technology",
            contact_email="careers@northstar.example.com",
        )
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(reverse("ipc-company-verify", args=[company.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company.refresh_from_db()
        self.assertEqual(company.verification_status, Company.VerificationStatus.VERIFIED)
        self.assertEqual(company.verified_by, self.ipc_admin)

    def test_non_ipc_user_cannot_verify_company(self):
        company = Company.objects.create(
            name="Northstar Technologies", industry="Technology",
            contact_email="careers@northstar.example.com",
        )
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(reverse("ipc-company-verify", args=[company.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_rejection_requires_reason(self):
        company = Company.objects.create(
            name="Northstar Technologies", industry="Technology",
            contact_email="careers@northstar.example.com",
        )
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-company-reject", args=[company.pk]), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RecruiterOpportunityWorkflowTests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="recruiter-two", email="recruiter-two@example.com",
            password="StrongPass123!secure", role=User.Role.RECRUITER,
        )
        self.ipc_admin = User.objects.create_user(
            username="ipc-admin-two", email="ipc-admin-two@example.com",
            password="StrongPass123!secure", role=User.Role.IPC_ADMIN,
        )
        self.student = User.objects.create_user(
            username="student-two", email="student-two@example.com",
            password="StrongPass123!secure", role=User.Role.STUDENT,
        )
        self.company = Company.objects.create(
            name="Verified Labs", industry="Technology",
            contact_email="careers@verified.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=self.company)
        self.url = reverse("recruiter-opportunity-list")
        self.data = {
            "title": "Backend Software Engineer Intern",
            "description": "Work with our team to build and maintain backend services and APIs.",
            "opportunity_type": "INTERNSHIP",
            "required_skills": ["Python", "Django", "PostgreSQL"],
            "eligibility_criteria": {
                "minimum_cgpa": 7.0,
                "graduation_years": [2027, 2028],
                "degree_programmes": ["B.Tech"],
                "departments": ["Computer Science"],
            },
            "work_mode": "HYBRID",
            "location": "Chennai, India",
            "compensation": "25000.00",
            "application_deadline": (timezone.now() + timedelta(days=30)).isoformat(),
            "application_method": "EXTERNAL",
            "external_application_url": "https://jobs.example.com/backend-intern",
        }

    def create_opportunity(self):
        return Opportunity.objects.create(
            company=self.company,
            created_by=self.recruiter,
            title=self.data["title"],
            description=self.data["description"],
            opportunity_type=self.data["opportunity_type"],
            required_skills=self.data["required_skills"],
            eligibility_criteria=self.data["eligibility_criteria"],
            work_mode=self.data["work_mode"],
            location=self.data["location"],
            application_deadline=timezone.now() + timedelta(days=30),
            application_method="EXTERNAL",
            external_application_url=self.data["external_application_url"],
            status=Opportunity.Status.DRAFT,
        )

    def test_recruiter_can_create_draft_opportunity(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Opportunity.Status.DRAFT)
        self.assertEqual(response.data["company_name"], self.company.name)

    def test_student_cannot_create_opportunity(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_without_company_cannot_create_opportunity(self):
        user = User.objects.create_user(
            username="recruiter-no-company", email="no-company@example.com",
            password="StrongPass123!secure", role=User.Role.RECRUITER,
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_minimum_cgpa_is_rejected(self):
        self.client.force_authenticate(user=self.recruiter)
        payload = {**self.data, "eligibility_criteria": {"minimum_cgpa": 12}}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unverified_company_cannot_submit_opportunity(self):
        self.company.verification_status = Company.VerificationStatus.PENDING
        self.company.save(update_fields=["verification_status"])
        opportunity = self.create_opportunity()
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(
            reverse("recruiter-opportunity-submit", args=[opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, Opportunity.Status.DRAFT)

    def test_verified_recruiter_can_submit_opportunity(self):
        opportunity = self.create_opportunity()
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(
            reverse("recruiter-opportunity-submit", args=[opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, Opportunity.Status.PENDING_APPROVAL)
        self.assertTrue(WorkflowAuditEvent.objects.filter(
            action=WorkflowAuditEvent.Action.OPPORTUNITY_SUBMITTED,
            object_id=opportunity.pk,
        ).exists())

    def test_recruiter_sees_only_own_company_opportunities(self):
        own = self.create_opportunity()
        other_company = Company.objects.create(
            name="Other Labs", industry="Technology",
            contact_email="careers@other.example.com",
        )
        other_recruiter = User.objects.create_user(
            username="other-recruiter", email="other-recruiter@example.com",
            password="StrongPass123!secure", role=User.Role.RECRUITER,
        )
        other = Opportunity.objects.create(
            company=other_company,
            created_by=other_recruiter,
            title="Other opportunity",
            description="A separate opportunity description.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            application_deadline=timezone.now() + timedelta(days=20),
        )
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(self.url)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(own.pk, ids)
        self.assertNotIn(other.pk, ids)

    def test_ipc_admin_can_approve_pending_opportunity(self):
        opportunity = self.create_opportunity()
        opportunity.status = Opportunity.Status.PENDING_APPROVAL
        opportunity.save(update_fields=["status"])
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-opportunity-approve", args=[opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, Opportunity.Status.PUBLISHED)
        self.assertEqual(opportunity.approved_by, self.ipc_admin)
        self.assertIsNotNone(opportunity.published_at)

    def test_non_ipc_user_cannot_approve_opportunity(self):
        opportunity = self.create_opportunity()
        opportunity.status = Opportunity.Status.PENDING_APPROVAL
        opportunity.save(update_fields=["status"])
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.post(
            reverse("ipc-opportunity-approve", args=[opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ipc_rejection_requires_reason(self):
        opportunity = self.create_opportunity()
        opportunity.status = Opportunity.Status.PENDING_APPROVAL
        opportunity.save(update_fields=["status"])
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-opportunity-reject", args=[opportunity.pk]), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ipc_can_reject_with_reason(self):
        opportunity = self.create_opportunity()
        opportunity.status = Opportunity.Status.PENDING_APPROVAL
        opportunity.save(update_fields=["status"])
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-opportunity-reject", args=[opportunity.pk]),
            {"reason": "Please clarify the eligibility requirements."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, Opportunity.Status.REJECTED)
        self.assertTrue(opportunity.rejection_reason)
