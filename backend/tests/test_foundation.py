import pytest
import yaml
from django.urls import reverse

from api.core.pagination import TeamPageNumberPagination


def test_pagination_defaults_and_limits_follow_team_contract():
    assert TeamPageNumberPagination.page_size == 20
    assert TeamPageNumberPagination.page_size_query_param == "page_size"
    assert TeamPageNumberPagination.max_page_size == 50


@pytest.mark.django_db
def test_role_fixtures_use_distinct_test_groups(
    student_user,
    recruiter_user,
    ipc_admin_user,
    alumni_user,
    system_admin_user,
):
    role_users = {
        "Student": student_user,
        "Recruiter": recruiter_user,
        "IPC Admin": ipc_admin_user,
        "Alumni": alumni_user,
        "System Admin": system_admin_user,
    }

    assert len({user.pk for user in role_users.values()}) == len(role_users)
    for role, user in role_users.items():
        assert list(user.groups.values_list("name", flat=True)) == [role]


def test_api_schema_is_generated_from_registered_routes(client):
    response = client.get(reverse("api-schema"))

    assert response.status_code == 200
    schema = yaml.safe_load(response.content)
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Nexus Career API"
    assert schema["paths"] == {}


@pytest.mark.parametrize("name", ["swagger-ui", "redoc"])
def test_interactive_documentation_routes_resolve(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]
