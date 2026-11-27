from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applications.models import Application, ApplicationStatusHistory
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile

User = get_user_model()


class EligibilityAndApplicationAPITests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.student = User.objects.create_user(
            username="eligible-student",
            email="eligible@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="other-student",
            email="other@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.recruiter = User.objects.create_user(
            username="application-recruiter",
            email="application-recruiter@example.com",
            password="StrongPass123!",
            role=User.Role.RECRUITER,
        )
        self.company = Company.objects.create(
            name="Application Test Company",
            industry="Technology",
            contact_email="careers@example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=self.company)
        self.opportunity = self.create_opportunity()
        self.client.force_authenticate(user=self.student)

    def tearDown(self):
        super().tearDown()

    def create_opportunity(self, **overrides):
        data = {
            "company": self.company,
            "created_by": self.recruiter,
            "title": "Backend Engineer",
            "description": "Build and maintain reliable backend services.",
            "opportunity_type": Opportunity.OpportunityType.JOB,
            "required_skills": ["Python", "Django"],
            "eligibility_criteria": {
                "minimum_cgpa": 7.0,
                "graduation_years": [2027, 2028],
                "degree_programmes": ["B.Tech"],
                "departments": ["Computer Science"],
            },
            "work_mode": Opportunity.WorkMode.REMOTE,
            "location": "Chennai",
            "application_deadline": timezone.now() + timedelta(days=10),
            "application_method": "PLATFORM",
            "status": Opportunity.Status.PUBLISHED,
            "published_at": timezone.now(),
        }
        data.update(overrides)
        return Opportunity.objects.create(**data)

    def create_profile(self, user=None, **overrides):
        user = user or self.student
        data = {
            "department": "Computer Science",
            "degree_programme": "B.Tech",
            "graduation_year": 2027,
            "cgpa": "8.40",
            "skills": ["Python", "Django", "SQL"],
        }
        data.update(overrides)
        profile = StudentProfile.objects.create(user=user, **data)
        profile.resume.save(
            "student-resume.pdf",
            SimpleUploadedFile(
                "student-resume.pdf",
                b"%PDF-1.7\nstudent resume fixture",
                content_type="application/pdf",
            ),
        )
        return profile

    def test_eligibility_returns_met_checks_for_matching_profile(self):
        self.create_profile()
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ELIGIBLE")
        self.assertTrue(response.data["eligible"])
        self.assertTrue(response.data["ready_to_apply"])
        self.assertEqual(
            {check["key"] for check in response.data["checks"]},
            {"cgpa", "graduation_year", "degree_programme", "department", "skills"},
        )

    def test_eligibility_explains_each_unmet_criterion(self):
        self.create_profile(cgpa="6.20", graduation_year=2026, skills=["Java"])
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.data["status"], "INELIGIBLE")
        self.assertFalse(response.data["eligible"])
        failed = {check["key"] for check in response.data["checks"] if check["status"] == "NOT_MET"}
        self.assertEqual(failed, {"cgpa", "graduation_year", "skills"})
        self.assertTrue(response.data["reasons"])

    def test_missing_criteria_information_is_incomplete_not_ineligible(self):
        StudentProfile.objects.create(
            user=self.student,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2027,
            cgpa=None,
            skills=[],
        )
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.data["status"], "INCOMPLETE_PROFILE")
        self.assertIsNone(response.data["eligible"])
        self.assertIn("CGPA", response.data["missing_fields"])
        self.assertIn("Required skills", response.data["missing_fields"])

    def test_missing_profile_is_reported_as_incomplete(self):
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.data["status"], "INCOMPLETE_PROFILE")
        self.assertIsNone(response.data["eligible"])
        self.assertIn("student profile", response.data["missing_fields"])

    def test_eligible_student_can_submit_application_and_resume_snapshot(self):
        profile = self.create_profile()
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = Application.objects.get(student=self.student, opportunity=self.opportunity)
        self.assertEqual(application.status, Application.Status.SUBMITTED)
        self.assertTrue(application.resume.name.startswith("private/application-resumes/"))
        with application.resume.open("rb") as submitted_resume:
            self.assertIn(b"student resume fixture", submitted_resume.read())
        self.assertEqual(ApplicationStatusHistory.objects.filter(application=application).count(), 1)
        self.assertEqual(response.data["opportunity_title"], self.opportunity.title)
        self.assertTrue(response.data["eligibility_snapshot"]["eligible"])
        profile.resume.delete(save=False)

    def test_duplicate_application_returns_conflict(self):
        self.create_profile()
        self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_student_cannot_apply_when_ineligible(self):
        self.create_profile(cgpa="6.00")
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("eligibility", response.data)
        self.assertEqual(Application.objects.count(), 0)

    def test_student_must_upload_resume_before_platform_application(self):
        StudentProfile.objects.create(
            user=self.student,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2027,
            cgpa="8.40",
            skills=["Python", "Django"],
        )
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", response.data)
        self.assertEqual(Application.objects.count(), 0)

    def test_duplicate_application_is_scoped_to_the_owning_student(self):
        self.create_profile()
        self.create_profile(user=self.other_student)
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(user=self.other_student)
        second = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Application.objects.filter(opportunity=self.opportunity).count(), 2)

    def test_student_can_only_see_own_application_tracking_records(self):
        self.create_profile()
        self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(reverse("application-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_external_opportunity_returns_company_url_and_is_not_platform_submittable(self):
        external = self.create_opportunity(
            application_method="EXTERNAL",
            external_application_url="https://careers.example.com/apply/123",
        )
        self.create_profile()
        eligibility = self.client.get(
            reverse("opportunity-eligibility", args=[external.pk])
        )
        self.assertTrue(eligibility.data["ready_to_apply"])
        self.assertEqual(
            eligibility.data["external_application_url"],
            "https://careers.example.com/apply/123",
        )
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": external.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Application.objects.filter(opportunity=external).count(), 0)

    def test_closed_or_expired_opportunity_cannot_be_applied_to(self):
        self.create_profile()
        expired = self.create_opportunity(
            application_deadline=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": expired.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_student_cannot_access_eligibility_or_applications(self):
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(
            reverse("opportunity-eligibility", args=[self.opportunity.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(reverse("application-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
