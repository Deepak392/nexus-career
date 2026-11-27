from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.applications.models import Application
from apps.notifications.models import Notification
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile
from apps.students.models import StudentProfile

User = get_user_model()


class ApplicationSubmissionNotificationTests(APITestCase):
    def setUp(self):
        self.temp_media = TemporaryDirectory()
        override = override_settings(MEDIA_ROOT=self.temp_media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(self.temp_media.cleanup)

        self.student = User.objects.create_user(
            username="notification-applicant",
            email="notification-applicant@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        recruiter = User.objects.create_user(
            username="notification-recruiter",
            email="notification-recruiter@example.com",
            password="StrongPass123!",
            role=User.Role.RECRUITER,
        )
        company = Company.objects.create(
            name="Notification Test Company",
            industry="Technology",
            contact_email="careers@notification.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        self.opportunity = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="Notification Test Role",
            description="A sufficiently detailed opportunity for notification testing.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            required_skills=["Python"],
            eligibility_criteria={"minimum_cgpa": 7.0, "graduation_years": [2027]},
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Chennai",
            application_deadline=timezone.now() + timedelta(days=7),
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
        profile.resume.save(
            "client-supplied-name.pdf",
            SimpleUploadedFile(
                "client-supplied-name.pdf",
                b"%PDF-1.7\nnotification test resume",
                content_type="application/pdf",
            ),
        )
        self.client.force_authenticate(user=self.student)

    def test_application_submission_creates_persistent_in_app_notification(self):
        response = self.client.post(
            reverse("application-list"),
            {"opportunity_id": self.opportunity.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = Application.objects.get(pk=response.data["id"])
        notification = Notification.objects.get(application=application)
        self.assertEqual(notification.recipient, self.student)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.APPLICATION_SUBMITTED,
        )
        self.assertIn(self.opportunity.title, notification.message)
        self.assertIsNone(notification.read_at)
        self.assertNotIn("client-supplied-name", application.resume.name)
        self.assertTrue(application.resume.name.endswith(".pdf"))
