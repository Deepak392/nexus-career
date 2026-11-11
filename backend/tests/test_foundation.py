from django.test import SimpleTestCase
from django.urls import reverse

from api.core import events
from api.core.pagination import TeamPageNumberPagination


class FoundationTests(SimpleTestCase):
    def test_pagination_defaults_and_limits_follow_team_contract(self):
        self.assertEqual(TeamPageNumberPagination.page_size, 20)
        self.assertEqual(
            TeamPageNumberPagination.page_size_query_param,
            "page_size",
        )
        self.assertEqual(TeamPageNumberPagination.max_page_size, 50)

    def test_versioned_application_routes_are_registered(self):
        self.assertEqual(reverse("account-register"), "/api/v1/auth/register/")
        self.assertEqual(reverse("student-profile"), "/api/v1/students/profile/")
        self.assertEqual(reverse("alumni-profile"), "/api/v1/alumni/profile/")
        self.assertEqual(reverse("opportunity-list"), "/api/v1/opportunities/")

    def test_api_schema_contains_registered_routes(self):
        response = self.client.get(reverse("api-schema"))

        self.assertEqual(response.status_code, 200)
        schema = response.content.decode("utf-8")
        self.assertIn("/api/v1/auth/register/", schema)
        self.assertIn("/api/v1/students/profile/", schema)
        self.assertIn("/api/v1/alumni/profile/", schema)

    def test_interactive_documentation_routes_resolve(self):
        for name in ("swagger-ui", "redoc"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response["Content-Type"])
                
    def test_event_handler_receives_emitted_payload(self):
            received = []

            def handler(payload):
                received.append(payload)

            events.register_handler("test.event", handler)

            payload = {"application_id": 123}
            events.emit("test.event", payload)

            self.assertEqual(received, [payload])

    def test_registering_same_handler_twice_does_not_duplicate_dispatch(self):
        received = []

        def handler(payload):
            received.append(payload)

        events.register_handler("test.duplicate", handler)
        events.register_handler("test.duplicate", handler)

        events.emit("test.duplicate", {"id": 1})

        self.assertEqual(len(received), 1)
        
    def test_handler_failure_does_not_break_event_dispatch(self):
        received = []

        def failing_handler(payload):
            raise RuntimeError("Notification failed")

        def successful_handler(payload):
            received.append(payload)

        events.register_handler("test.failure", failing_handler)
        events.register_handler("test.failure", successful_handler)

        payload = {"application_id": 123}
        events.emit("test.failure", payload)

        self.assertEqual(received, [payload])