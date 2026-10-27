from itertools import count

import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient


ROLE_NAMES = ("Student", "Recruiter", "IPC Admin", "Alumni", "System Admin")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    usernames = count(1)

    def make_user(*, username=None, password="test-only-password", **fields):
        username = username or f"test-user-{next(usernames)}"
        return User.objects.create_user(username=username, password=password, **fields)

    return make_user


@pytest.fixture
def role_user_factory(user_factory):
    """Test-only adapter using Django Groups until the shared role model is agreed."""

    def make_role_user(role, **fields):
        if role not in ROLE_NAMES:
            raise ValueError(f"Unknown test role: {role}")
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
