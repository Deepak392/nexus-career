from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.alumni.models import AlumniProfile


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
        response = self.client.post(
            self.url, self.valid_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AlumniProfile.objects.filter(user=self.alumni).exists()
        )

    def test_alumni_can_view_own_profile(self):
        AlumniProfile.objects.create(
            user=self.alumni,
            **self.valid_data,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_company"], "Google")

    def test_alumni_can_update_own_profile(self):
        AlumniProfile.objects.create(
            user=self.alumni,
            **self.valid_data,
        )

        response = self.client.patch(
            self.url,
            {"current_company": "Microsoft"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_company"], "Microsoft")

    def test_alumni_cannot_create_duplicate_profile(self):
        AlumniProfile.objects.create(
            user=self.alumni,
            **self.valid_data,
        )

        response = self.client.post(
            self.url, self.valid_data, format="json"
        )

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
            **{
                **self.valid_data,
                "verification_status": AlumniProfile.VerificationStatus.VERIFIED,
            },
        )

        AlumniProfile.objects.create(
            user=pending_user,
            **self.valid_data,
        )

        response = self.client.get(
            reverse("alumni-search"),
            {"company": "Google"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_search_filters_by_designation(self):
        AlumniProfile.objects.create(
            user=self.alumni,
            **{
                **self.valid_data,
                "verification_status": AlumniProfile.VerificationStatus.VERIFIED,
            },
        )

        response = self.client.get(
            reverse("alumni-search"),
            {"designation": "Software Engineer"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)