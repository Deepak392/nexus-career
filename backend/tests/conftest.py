from itertools import count
import tempfile
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.core.audit import clear_audit_logs
from api.core.events import clear_emitted_events
from apps.alumni.models import AlumniProfile
from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile


ROLE_NAMES = (
    "Student",
    "Recruiter",
    "IPC Admin",
    "Alumni",
    "System Admin",
)


@pytest.fixture(autouse=True)
def reset_audit_and_event_stores():
    """Cleans in-memory audit logs and emitted events between test cases."""
    clear_audit_logs()
    clear_emitted_events()
    yield
    clear_audit_logs()
    clear_emitted_events()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def jwt_auth_headers():
    def _generate_headers(user):
        refresh = RefreshToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {str(refresh.access_token)}"}

    return _generate_headers


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


@pytest.fixture
def company_factory(db):
    companies = count(1)

    def make_company(**kwargs):
        idx = next(companies)
        kwargs.setdefault("name", f"Tech Innovations {idx} Corp")
        kwargs.setdefault("industry", "Software Engineering")
        kwargs.setdefault("contact_email", f"contact{idx}@techcorp.test")
        kwargs.setdefault("verification_status", Company.VerificationStatus.PENDING)
        return Company.objects.create(**kwargs)

    return make_company


@pytest.fixture
def pending_recruiter(db, role_user_factory, company_factory):
    user = role_user_factory("Recruiter")
    company = company_factory(verification_status=Company.VerificationStatus.PENDING)
    profile = RecruiterProfile.objects.create(
        user=user,
        company=company,
        designation="Lead Campus Recruiter",
        work_email=user.email,
    )
    return profile


@pytest.fixture
def verified_company(db, company_factory, ipc_admin_user):
    return company_factory(
        name="Verified Enterprise Corp",
        verification_status=Company.VerificationStatus.VERIFIED,
        verified_by=ipc_admin_user,
        verified_at=timezone.now(),
    )


@pytest.fixture
def pending_alumni_profile(db, role_user_factory):
    user = role_user_factory("Alumni")
    proof = SimpleUploadedFile(
        name="degree_certificate.pdf",
        content=b"%PDF-1.4 Mock Degree Certificate Content",
        content_type="application/pdf",
    )
    profile = AlumniProfile.objects.create(
        user=user,
        department="Computer Science and Engineering",
        degree_programme="B.Tech Computer Science",
        graduation_year=2024,
        current_company="Acme Software Labs",
        designation="Software Development Engineer",
        verification_status=AlumniProfile.VerificationStatus.PENDING,
        graduation_proof=proof,
    )
    return profile


@pytest.fixture
def opportunity_factory(db, verified_company, recruiter_user):
    opps = count(1)

    def make_opportunity(**kwargs):
        idx = next(opps)
        kwargs.setdefault("company", verified_company)
        kwargs.setdefault("created_by", recruiter_user)
        kwargs.setdefault("title", f"Software Development Engineer {idx}")
        kwargs.setdefault("description", "Join our innovative platform engineering team.")
        kwargs.setdefault("opportunity_type", Opportunity.OpportunityType.JOB)
        kwargs.setdefault("work_mode", Opportunity.WorkMode.REMOTE)
        kwargs.setdefault("location", "Hyderabad, India")
        kwargs.setdefault("compensation", 1200000.00)
        kwargs.setdefault("application_deadline", timezone.now() + timezone.timedelta(days=30))
        kwargs.setdefault("status", Opportunity.Status.PENDING_APPROVAL)
        return Opportunity.objects.create(**kwargs)

    return make_opportunity
