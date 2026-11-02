
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.students.models import StudentProfile


User = get_user_model()


class StudentProfileAPITests(APITestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username="student1",
            email="student@example.com",
            password="TestPassword123!",
            role=User.Role.STUDENT,
        )

        self.client.force_authenticate(user=self.student)
        self.url = reverse("student-profile")

        self.valid_data = {
            "department": "Computer Science",
            "degree_programme": "B.Tech",
            "graduation_year": 2027,
            "cgpa": "8.50",
            "skills": ["Python", "SQL"],
            "areas_of_interest": ["Data Science"],
            "experience": "Academic projects",
            "preferred_roles": ["Data Analyst"],
            "preferred_locations": ["Hyderabad"],
            "work_mode": "HYBRID",
        }

    def test_student_can_create_profile(self):
        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            StudentProfile.objects.filter(user=self.student).exists()
        )

    def test_student_can_view_own_profile(self):
        StudentProfile.objects.create(
            user=self.student,
            **self.valid_data,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["department"], "Computer Science")

    def test_student_can_update_own_profile(self):
        StudentProfile.objects.create(
            user=self.student,
            **self.valid_data,
        )

        response = self.client.patch(
            self.url,
            {"department": "Data Science"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["department"],
            "Data Science",
        )

    def test_student_cannot_create_duplicate_profile(self):
        StudentProfile.objects.create(
            user=self.student,
            **self.valid_data,
        )

        response = self.client.post(
            self.url,
            self.valid_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_student_cannot_access_student_profile(self):
        recruiter = User.objects.create_user(
            username="recruiter1",
            email="recruiter@example.com",
            password="TestPassword123!",
            role=User.Role.RECRUITER,
        )

        self.client.force_authenticate(user=recruiter)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
