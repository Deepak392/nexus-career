from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile

User = get_user_model()


class AlreadyAppliedEligibilityTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="already-applied-student",
            email="already-applied@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        recruiter = User.objects.create_user(
            username="already-applied-recruiter",
            email="already-applied-recruiter@example.com",
            password="StrongPass123!",
            role=User.Role.RECRUITER,
        )
        company = Company.objects.create(
            name="Eligibility State Company",
            industry="Technology",
            contact_email="jobs@eligibility-state.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        self.opportunity = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="Already Applied Role",
            description="An opportunity for testing existing application state.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            required_skills=["Python"],
            eligibility_criteria={"minimum_cgpa": 7.0},
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Chennai",
            application_deadline=timezone.now() + timedelta(days=5),
            application_method="PLATFORM",
            status=Opportunity.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        profile = StudentProfile.objects.create(
            user=self.student,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2027,
            cgpa="8.50",
            skills=["Python"],
        )
        Application.objects.create(
            student=self.student,
            opportunity=self.opportunity,
            resume="private/application-resumes/submitted-resume.pdf",
            eligibility_snapshot={"status": "ELIGIBLE", "eligible": True},
        )
        self.client.force_authenticate(user=self.student)

    def test_eligibility_endpoint_reports_existing_application(self):
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["already_applied"])
        self.assertFalse(response.data["ready_to_apply"])
