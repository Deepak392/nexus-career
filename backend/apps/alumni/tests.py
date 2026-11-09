from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.alumni.models import AlumniProfile, ReferralRequest, ReferralRequestHistory
from apps.notifications.models import Notification


User = get_user_model()


class AlumniProfileAPITests(APITestCase):
    def setUp(self):
        self.alumni = User.objects.create_user(
            username="alumni1",
            email="alumni1@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        self.client.force_authenticate(user=self.alumni)
        self.url = reverse("alumni-profile")
        self.valid_data = {
            "department": "Computer Science",
            "degree_programme": "B.Tech",
            "graduation_year": 2024,
            "current_company": "Google",
            "designation": "Software Engineer",
            "industry": "Technology",
            "is_open_to_referrals": True,
        }

    def test_alumni_can_create_profile(self):
        response = self.client.post(self.url, self.valid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AlumniProfile.objects.filter(user=self.alumni).exists())

    def test_alumni_can_view_own_profile(self):
        AlumniProfile.objects.create(user=self.alumni, **self.valid_data)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_company"], "Google")
        self.assertEqual(response.data["email"], self.alumni.email)

    def test_alumni_can_update_own_profile(self):
        AlumniProfile.objects.create(user=self.alumni, **self.valid_data)
        response = self.client.patch(
            self.url, {"current_company": "Microsoft"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_company"], "Microsoft")

    def test_alumni_can_toggle_referral_availability(self):
        AlumniProfile.objects.create(user=self.alumni, **self.valid_data)
        response = self.client.patch(
            self.url, {"is_open_to_referrals": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_open_to_referrals"])

    def test_alumni_cannot_create_duplicate_profile(self):
        AlumniProfile.objects.create(user=self.alumni, **self.valid_data)
        response = self.client.post(self.url, self.valid_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_alumni_cannot_access_alumni_profile(self):
        student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_returns_only_verified_alumni(self):
        verified_user = User.objects.create_user(
            username="verified1",
            email="verified1@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        pending_user = User.objects.create_user(
            username="pending1",
            email="pending1@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        AlumniProfile.objects.create(
            user=verified_user,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
            **self.valid_data,
        )
        AlumniProfile.objects.create(user=pending_user, **self.valid_data)

        student = User.objects.create_user(
            username="searchstudent",
            email="searchstudent@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=student)
        response = self.client.get(reverse("alumni-search"), {"company": "Google"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_search_can_filter_referral_availability(self):
        verified_user = User.objects.create_user(
            username="available1",
            email="available1@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        AlumniProfile.objects.create(
            user=verified_user,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
            is_open_to_referrals=False,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2020,
        )
        student = User.objects.create_user(
            username="searchstudent2",
            email="searchstudent2@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.client.force_authenticate(user=student)
        response = self.client.get(reverse("alumni-search"), {"available": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)


@override_settings(MEDIA_ROOT="/tmp/nexus-career-alumni-tests")
class AlumniReferralWorkflowTests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="referralstudent",
            first_name="Ravi",
            last_name="Kumar",
            email="ravi.student@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.alumni_user = User.objects.create_user(
            username="referralalumni",
            first_name="Ananya",
            last_name="Sharma",
            email="ananya.alumni@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        self.other_alumni = User.objects.create_user(
            username="otheralumni",
            email="other.alumni@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        self.profile = AlumniProfile.objects.create(
            user=self.alumni_user,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2020,
            current_company="Example Tech",
            designation="Software Engineer",
            industry="Technology",
            is_open_to_referrals=True,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
        )
        self.other_profile = AlumniProfile.objects.create(
            user=self.other_alumni,
            department="Electrical Engineering",
            degree_programme="B.Tech",
            graduation_year=2019,
            current_company="Other Corp",
            designation="Engineer",
            industry="Engineering",
            is_open_to_referrals=True,
            verification_status=AlumniProfile.VerificationStatus.VERIFIED,
        )
        self.list_url = reverse("alumni-referral-list-create")
        self.opportunity_url = "https://careers.example.com/jobs/software-engineer"

    def pdf_upload(self):
        return SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4\nNexus Career referral resume test",
            content_type="application/pdf",
        )

    def submit_request(self, alumni_profile=None):
        return self.client.post(
            self.list_url,
            {
                "alumni_profile_id": alumni_profile or self.profile.pk,
                "opportunity_url": self.opportunity_url,
                "resume": self.pdf_upload(),
                "note": "I am interested in this software engineering role.",
            },
            format="multipart",
        )

    def create_request(self):
        self.client.force_authenticate(user=self.student)
        response = self.submit_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return ReferralRequest.objects.get(pk=response.data["id"])

    def test_student_can_submit_referral_request_with_resume_and_note(self):
        self.client.force_authenticate(user=self.student)
        response = self.submit_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        referral = ReferralRequest.objects.get(pk=response.data["id"])
        self.assertEqual(referral.student, self.student)
        self.assertEqual(referral.alumni_profile, self.profile)
        self.assertEqual(referral.status, ReferralRequest.Status.PENDING)
        self.assertTrue(referral.resume.name)
        self.assertEqual(referral.history.count(), 1)
        notification = Notification.objects.get(
            recipient=self.alumni_user,
            referral_request=referral,
        )
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.REFERRAL_REQUEST,
        )

    def test_only_verified_and_available_alumni_can_receive_requests(self):
        self.client.force_authenticate(user=self.student)
        self.other_profile.verification_status = AlumniProfile.VerificationStatus.PENDING
        self.other_profile.save(update_fields=["verification_status"])
        response = self.submit_request(self.other_profile.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.other_profile.verification_status = AlumniProfile.VerificationStatus.VERIFIED
        self.other_profile.is_open_to_referrals = False
        self.other_profile.save(update_fields=["verification_status", "is_open_to_referrals"])
        response = self.submit_request(self.other_profile.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_submit_referral_request_for_another_student(self):
        recruiter = User.objects.create_user(
            username="referralrecruiter",
            email="referralrecruiter@example.com",
            password="TestPassword123!",
            role=User.Role.RECRUITER,
        )
        self.client.force_authenticate(user=recruiter)
        response = self.submit_request()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_active_referral_request_is_rejected(self):
        self.create_request()
        self.client.force_authenticate(user=self.student)
        response = self.submit_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alumni_only_sees_assigned_referral_requests(self):
        referral = self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], referral.pk)

        self.client.force_authenticate(user=self.other_alumni)
        response = self.client.get(reverse("alumni-referral-detail", args=[referral.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_alumni_can_accept_and_mark_accepted_request_as_referred(self):
        referral = self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        accept = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "accept"]),
            {"note": "Happy to help."},
            format="json",
        )
        self.assertEqual(accept.status_code, status.HTTP_200_OK, accept.data)
        self.assertEqual(accept.data["status"], ReferralRequest.Status.ACCEPTED)

        referred = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "mark-referred"]),
            {"note": "Referred through the company portal."},
            format="json",
        )
        self.assertEqual(referred.status_code, status.HTTP_200_OK, referred.data)
        self.assertEqual(referred.data["status"], ReferralRequest.Status.REFERRED)
        self.assertEqual(
            ReferralRequestHistory.objects.filter(referral_request=referral).count(),
            3,
        )
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.student,
                referral_request=referral,
            ).count(),
            2,
        )

    def test_alumni_can_decline_pending_request(self):
        referral = self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        response = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "decline"]),
            {"note": "I cannot refer for this opening."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ReferralRequest.Status.DECLINED)

    def test_more_information_request_and_student_response_are_tracked(self):
        referral = self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        request_info = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "request-information"]),
            {"note": "Please share your latest project experience."},
            format="json",
        )
        self.assertEqual(request_info.status_code, status.HTTP_200_OK)
        self.assertEqual(request_info.data["status"], ReferralRequest.Status.PENDING)

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "respond"]),
            {"note": "I recently completed a production full-stack project."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ReferralRequest.Status.PENDING)
        self.assertEqual(len(response.data["history"]), 3)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.alumni_user,
                referral_request=referral,
            ).count(),
            1,
        )

    def test_cannot_mark_pending_request_as_referred(self):
        referral = self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        response = self.client.post(
            reverse("alumni-referral-action", args=[referral.pk, "mark-referred"]),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resume_download_is_restricted_to_request_participants(self):
        referral = self.create_request()
        url = reverse("alumni-referral-resume", args=[referral.pk])

        self.client.force_authenticate(user=self.other_alumni)
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.alumni_user)
        allowed = self.client.get(url)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed["Content-Type"], "application/pdf")

    def test_alumni_metrics_are_derived_from_real_referral_data(self):
        self.create_request()
        self.client.force_authenticate(user=self.alumni_user)
        response = self.client.get(reverse("alumni-metrics"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["pending"], 1)
        self.assertEqual(response.data["student_interactions"], 1)
        self.assertTrue(response.data["is_open_to_referrals"])


class AlumniVerificationWorkflowTests(APITestCase):
    def setUp(self):
        self.ipc_admin = User.objects.create_user(
            username="ipc-alumni-reviewer",
            email="ipc-alumni-reviewer@example.com",
            password="TestPassword123!",
            role=User.Role.IPC_ADMIN,
        )
        self.student = User.objects.create_user(
            username="alumni-review-student",
            email="alumni-review-student@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )
        self.alumni = User.objects.create_user(
            username="pending-alumni-review",
            email="pending-alumni-review@example.com",
            password="TestPassword123!",
            role=User.Role.ALUMNI,
        )
        self.profile = AlumniProfile.objects.create(
            user=self.alumni,
            department="Computer Science",
            degree_programme="B.Tech",
            graduation_year=2022,
            current_company="Example Tech",
            designation="Developer",
            industry="Technology",
            verification_status=AlumniProfile.VerificationStatus.PENDING,
        )

    def test_only_ipc_admin_can_view_pending_alumni_queue(self):
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.get(reverse("ipc-pending-alumni"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.profile.pk)

        self.client.force_authenticate(user=self.student)
        denied = self.client.get(reverse("ipc-pending-alumni"))
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_ipc_admin_can_verify_alumni_and_notify_user(self):
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-alumni-verify", args=[self.profile.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.verification_status,
            AlumniProfile.VerificationStatus.VERIFIED,
        )
        self.assertEqual(self.profile.reviewed_by, self.ipc_admin)
        self.assertIsNotNone(self.profile.reviewed_at)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.alumni,
                notification_type=Notification.NotificationType.ALUMNI_VERIFICATION,
            ).exists()
        )

    def test_ipc_admin_can_reject_alumni_with_reason(self):
        self.client.force_authenticate(user=self.ipc_admin)
        response = self.client.post(
            reverse("ipc-alumni-reject", args=[self.profile.pk]),
            {"reason": "Please clarify your graduation information."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.verification_status,
            AlumniProfile.VerificationStatus.REJECTED,
        )
        self.assertEqual(
            self.profile.verification_rejection_reason,
            "Please clarify your graduation information.",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.alumni,
                title="Alumni profile needs attention",
            ).exists()
        )

    def test_recruiter_cannot_verify_alumni(self):
        recruiter = User.objects.create_user(
            username="alumni-review-recruiter",
            email="alumni-review-recruiter@example.com",
            password="TestPassword123!",
            role=User.Role.RECRUITER,
        )
        self.client.force_authenticate(user=recruiter)
        response = self.client.post(
            reverse("ipc-alumni-verify", args=[self.profile.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
