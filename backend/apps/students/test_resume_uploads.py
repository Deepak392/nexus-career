from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class StudentResumeUploadTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        override = override_settings(MEDIA_ROOT=self.media_directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.student = User.objects.create_user(
            username="resume-student",
            email="resume-student@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=self.student)
        self.url = reverse("student-profile")
        self.profile_data = {
            "department": "Computer Science",
            "degree_programme": "B.Tech",
            "graduation_year": 2027,
            "cgpa": "8.50",
            "skills": ["Python", "SQL"],
        }

    def test_student_can_upload_pdf_resume(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.7\nvalid PDF fixture",
            content_type="application/pdf",
        )
        response = self.client.post(
            self.url,
            {**self.profile_data, "resume": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["has_resume"])
        self.assertNotIn("resume", response.data)

        profile = self.student.student_profile
        self.assertTrue(profile.resume.name.startswith("private/student-resumes/"))

    def test_upload_rejects_file_without_pdf_signature(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            b"not a PDF file",
            content_type="application/pdf",
        )
        response = self.client.post(
            self.url,
            {**self.profile_data, "resume": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", response.data)

    def test_upload_rejects_file_larger_than_five_megabytes(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-" + (b"x" * (5 * 1024 * 1024)),
            content_type="application/pdf",
        )
        response = self.client.post(
            self.url,
            {**self.profile_data, "resume": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", response.data)
