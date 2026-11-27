# Security review: private-file access tests (SRS NFR-SEC-07, NFR-SEC-08, NFR-PRV-03).
# Uses fake accounts and fake PDFs only, in a temporary media folder.

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.alumni.models import AlumniProfile, ReferralRequest

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
PASSWORD = "TestPassword123!"


def make_user(username, role):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        role=role,
    )


def make_pdf(name="file.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class PrivateFileAccessTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.student = make_user("student_owner", User.Role.STUDENT)
        self.other_student = make_user("student_other", User.Role.STUDENT)
        self.alumni = make_user("alumni_owner", User.Role.ALUMNI)
        self.other_alumni = make_user("alumni_other", User.Role.ALUMNI)
        self.recruiter = make_user("recruiter_one", User.Role.RECRUITER)
        self.ipc_admin = make_user("ipc_one", User.Role.IPC_ADMIN)
        self.system_admin = make_user("sysadmin_one", User.Role.SYSTEM_ADMIN)

        self.alumni_profile = self.make_profile(self.alumni)
        self.other_alumni_profile = self.make_profile(self.other_alumni)

        self.referral = ReferralRequest.objects.create(
            student=self.student,
            alumni_profile=self.alumni_profile,
            opportunity_url="https://example.com/jobs/1",
            resume=make_pdf("resume.pdf"),
            note="Please refer me.",
        )
        self.resume_url = reverse("alumni-referral-resume", args=[self.referral.pk])
        self.proof_url = reverse(
            "ipc-alumni-graduation-proof", args=[self.alumni_profile.pk]
        )

    def make_profile(self, user):
        return AlumniProfile.objects.create(
            user=user,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2024,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
            is_open_to_referrals=True,
            graduation_proof=make_pdf("proof.pdf"),
        )

    def read_file(self, response):
        # The test client closes the response itself once the stream is fully read.
        # Calling response.close() here would close the test database connection.
        return b"".join(response.streaming_content)

    def check_denied(self, url, cases):
        for user, expected in cases:
            with self.subTest(user=getattr(user, "username", "anonymous")):
                self.client.force_authenticate(user=user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, expected)

    # Referral resume ---------------------------------------------------

    def test_referral_resume_is_denied_to_everyone_but_the_two_participants(self):
        self.check_denied(
            self.resume_url,
            [
                (None, status.HTTP_401_UNAUTHORIZED),
                (self.other_student, status.HTTP_404_NOT_FOUND),
                (self.other_alumni, status.HTTP_404_NOT_FOUND),
                (self.recruiter, status.HTTP_403_FORBIDDEN),
                (self.ipc_admin, status.HTTP_403_FORBIDDEN),
                (self.system_admin, status.HTTP_403_FORBIDDEN),
            ],
        )

    def test_student_who_sent_the_request_can_download_the_resume(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.resume_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertTrue(self.read_file(response).startswith(b"%PDF-"))

    def test_assigned_alumni_can_download_the_resume(self):
        self.client.force_authenticate(user=self.alumni)
        response = self.client.get(self.resume_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertTrue(self.read_file(response).startswith(b"%PDF-"))

    # Graduation proof --------------------------------------------------

    def test_graduation_proof_is_denied_to_everyone_but_ipc_admin(self):
        self.check_denied(
            self.proof_url,
            [
                (None, status.HTTP_401_UNAUTHORIZED),
                (self.student, status.HTTP_403_FORBIDDEN),
                (self.alumni, status.HTTP_403_FORBIDDEN),
                (self.other_alumni, status.HTTP_403_FORBIDDEN),
                (self.recruiter, status.HTTP_403_FORBIDDEN),
                (self.system_admin, status.HTTP_403_FORBIDDEN),
            ],
        )

    def test_ipc_admin_can_download_the_graduation_proof(self):
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.get(self.proof_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertTrue(self.read_file(response).startswith(b"%PDF-"))