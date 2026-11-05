
from itertools import count

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.core.audit import clear_audit_logs, get_audit_logs
from apps.alumni.models import AlumniProfile
from apps.recruiters.models import Company, RecruiterProfile


ROLE_NAMES = (
    "Student",
    "Recruiter",
    "IPC Admin",
    "Alumni",
    "System Admin",
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    User = get_user_model()
    usernames = count(1)

    def make_user(
        *,
        username=None,
        password="test-only-password",
        **fields,
    ):
        username = username or f"test-user-{next(usernames)}"
        fields.setdefault("email", f"{username}@scds.saiuniversity.edu.in")
        fields.setdefault("role", User.Role.STUDENT)

        return User.objects.create_user(
            username=username,
            password=password,
            **fields,
        )

    return make_user


@pytest.fixture
def role_user_factory(user_factory):
    User = get_user_model()

    role_values = {
        "Student": User.Role.STUDENT,
        "Recruiter": User.Role.RECRUITER,
        "IPC Admin": User.Role.IPC_ADMIN,
        "Alumni": User.Role.ALUMNI,
        "System Admin": User.Role.SYSTEM_ADMIN,
    }

    def make_role_user(role, **fields):
        if role not in ROLE_NAMES:
            raise ValueError(f"Unknown test role: {role}")

        fields.setdefault("role", role_values[role])

        user = user_factory(**fields)

        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        return user

    return make_role_user


@pytest.fixture
def student_user(role_user_factory):
    return role_user_factory("Student")


@pytest.fixture
def recruiter_user(role_user_factory):
    return role_user_factory("Recruiter")


@pytest.fixture
def ipc_admin_user(role_user_factory):
    return role_user_factory("IPC Admin")


@pytest.fixture
def alumni_user(role_user_factory):
    return role_user_factory("Alumni")


@pytest.fixture
def system_admin_user(role_user_factory):
    return role_user_factory("System Admin")


@pytest.fixture
def jwt_auth_headers():
    """Generates real SimpleJWT Bearer authentication headers for a given user."""
    def _headers(user):
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}
    return _headers


@pytest.fixture(autouse=True)
def reset_audit_log_store():
    """Cleans in-memory audit store before and after each test."""
    clear_audit_logs()
    yield
    clear_audit_logs()


@pytest.fixture
def company_factory(db):
    companies = count(1)

    def _make_company(**fields):
        num = next(companies)
        fields.setdefault("name", f"Tech Innovations {num}")
        fields.setdefault("industry", "Information Technology")
        fields.setdefault("contact_email", f"contact{num}@techinnovations.com")
        fields.setdefault("verification_status", Company.VerificationStatus.PENDING)
        return Company.objects.create(**fields)

    return _make_company


@pytest.fixture
def pending_company(company_factory):
    return company_factory()


@pytest.fixture
def pending_recruiter(recruiter_user, pending_company):
    return RecruiterProfile.objects.create(
        user=recruiter_user,
        company=pending_company,
        designation="Lead Technical Recruiter",
        work_email="recruiter@techinnovations.com",
    )


@pytest.fixture
def pending_alumni_profile(alumni_user):
    return AlumniProfile.objects.create(
        user=alumni_user,
        department="School of Computing and Data Science",
        degree_programme="B.Tech Computer Science",
        graduation_year=2024,
        current_company="Acme Corp",
        designation="Software Engineer",
        industry="Technology",
        verification_status=AlumniProfile.VerificationStatus.PENDING,
    )
