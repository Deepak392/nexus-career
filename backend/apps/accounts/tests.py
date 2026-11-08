from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.alumni.models import AlumniProfile


User = get_user_model()


class AuthenticationTests(APITestCase):

    def setUp(self):
        self.password = "TestPassword123!Secure"

        self.user = User.objects.create_user(
            username="existingstudent",
            email="existingstudent@scds.saiuniversity.edu.in",
            password=self.password,
            role=User.Role.STUDENT,
        )

    def test_student_registration(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "newstudent",
                "email": "newstudent@scds.saiuniversity.edu.in",
                "password": "AnotherSecurePassword123!X",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_user = User.objects.get(username="newstudent")

        self.assertEqual(new_user.role, User.Role.STUDENT)
        self.assertTrue(new_user.check_password("AnotherSecurePassword123!X"))

    def test_recruiter_registration_assigns_recruiter_role(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "newrecruiter",
                "email": "recruiter@example.com",
                "password": "AnotherSecurePassword123!X",
                "role": "RECRUITER",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recruiter = User.objects.get(username="newrecruiter")
        self.assertEqual(recruiter.role, User.Role.RECRUITER)
        self.assertEqual(response.data["role"], User.Role.RECRUITER)

        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": recruiter.username,
                "password": "AnotherSecurePassword123!X",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(profile_response.data["role"], User.Role.RECRUITER)

    def test_alumni_registration_creates_pending_profile_without_proof(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "newalumni",
                "email": "alumni@example.com",
                "password": "AnotherSecurePassword123!X",
                "role": "ALUMNI",
                "department": "Computer Science",
                "degree_programme": "B.Tech",
                "graduation_year": "2024",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alumni = User.objects.get(username="newalumni")
        profile = AlumniProfile.objects.get(user=alumni)

        self.assertEqual(alumni.role, User.Role.ALUMNI)
        self.assertEqual(response.data["role"], User.Role.ALUMNI)
        self.assertEqual(profile.department, "Computer Science")
        self.assertEqual(profile.degree_programme, "B.Tech")
        self.assertEqual(profile.graduation_year, 2024)
        self.assertFalse(profile.graduation_proof)
        self.assertEqual(
            profile.verification_status,
            AlumniProfile.VerificationStatus.PENDING,
        )

        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": alumni.username,
                "password": "AnotherSecurePassword123!X",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get("/api/v1/auth/me/")
        self.assertEqual(profile_response.data["role"], User.Role.ALUMNI)

    def test_alumni_registration_requires_academic_details(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "missingdetails",
                "email": "missingdetails@example.com",
                "password": "AnotherSecurePassword123!X",
                "role": "ALUMNI",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("department", response.data)
        self.assertIn("degree_programme", response.data)
        self.assertIn("graduation_year", response.data)
        self.assertFalse(User.objects.filter(username="missingdetails").exists())

    def test_registration_rejects_privileged_role_assignment(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "selfappointedadmin",
                "email": "admin@example.com",
                "password": "AnotherSecurePassword123!X",
                "role": "IPC_ADMIN",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            User.objects.filter(username="selfappointedadmin").exists()
        )

    def test_registration_rejects_invalid_student_email_domain(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "invalidstudent",
                "email": "student@example.com",
                "password": "AnotherSecurePassword123!X",
                "role": "STUDENT",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "duplicateuser",
                "email": "EXISTINGSTUDENT@scds.saiuniversity.edu.in",
                "password": "AnotherSecurePassword123!X",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_invalid_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_view_profile(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.user.username)
        self.assertEqual(response.data["role"], "STUDENT")
        self.assertNotIn("password", response.data)

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        logout_response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_205_RESET_CONTENT,
        )

        refresh_response = self.client.post(
            "/api/v1/auth/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_rejects_missing_refresh_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

        response = self.client.post(
            "/api/v1/auth/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_rejects_invalid_refresh_token(self):
        login_response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

        response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": "not-a-valid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_cannot_blacklist_another_users_token(self):
        other_user = User.objects.create_user(
            username="anotherstudent",
            email="anotherstudent@scds.saiuniversity.edu.in",
            password=self.password,
            role=User.Role.STUDENT,
        )

        other_client = APIClient()

        other_login = other_client.post(
            "/api/v1/auth/login/",
            {
                "username": other_user.username,
                "password": self.password,
            },
            format="json",
        )

        own_login = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": self.user.username,
                "password": self.password,
            },
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {own_login.data['access']}"
        )

        response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": other_login.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        refresh_response = other_client.post(
            "/api/v1/auth/refresh/",
            {"refresh": other_login.data["refresh"]},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

    def test_logout_requires_authentication(self):
        response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": "some-refresh-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
