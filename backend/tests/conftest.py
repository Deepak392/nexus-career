from apps.accounts.models import User
from itertools import count

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


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
        fields.setdefault("email", f"{username}@example.test")
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

from rest_framework_simplejwt.tokens import RefreshToken
from api.core.audit import clear_audit_logs
from apps.recruiters.models import Company, RecruiterProfile
from apps.alumni.models import AlumniProfile


@pytest.fixture
def jwt_auth_headers():
    def _headers(user):
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {refresh.access_token}"}
    return _headers


@pytest.fixture(autouse=True)
def reset_audit_log_store():
    clear_audit_logs()
    yield
    clear_audit_logs()


@pytest.fixture
def company_factory(db, user_factory):
    def _create_company(name="Acme Corp", recruiter=None, **kwargs):
        recruiter = recruiter or user_factory(role=User.Role.RECRUITER)
        company = Company.objects.create(
            name=name,
            website=kwargs.get("website", "https://acme.example.com"),
            industry=kwargs.get("industry", "Technology"),
            contact_email=kwargs.get("contact_email", "jobs@acme.example.com"),
            contact_phone=kwargs.get("contact_phone", "+1234567890"),
            description=kwargs.get("description", "A leading software company."),
            verification_status=kwargs.get("verification_status", Company.VerificationStatus.PENDING),
        )
        profile, _ = RecruiterProfile.objects.get_or_create(user=recruiter, defaults={"company": company})
        if profile.company_id != company.id:
            profile.company = company
            profile.save(update_fields=["company"])
        return company, profile
    return _create_company


@pytest.fixture
def pending_company(company_factory):
    company, _ = company_factory(name="Pending Tech Ltd", verification_status=Company.VerificationStatus.PENDING)
    return company


@pytest.fixture
def pending_recruiter(company_factory, recruiter_user):
    _, profile = company_factory(name="Recruiter Corp", recruiter=recruiter_user, verification_status=Company.VerificationStatus.PENDING)
    return profile


@pytest.fixture
def pending_alumni_profile(db, user_factory):
    alumni_user = user_factory(role=User.Role.ALUMNI)
    profile = AlumniProfile.objects.create(
        user=alumni_user,
        department="Computer Science",
        degree_programme="B.Tech",
        graduation_year=2023,
        current_company="Tech Solutions",
        designation="Software Engineer",
        industry="Technology",
        is_open_to_referrals=True,
        verification_status=AlumniProfile.VerificationStatus.PENDING,
    )
    return profile
