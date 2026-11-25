from django.test import SimpleTestCase


class HealthEndpointTests(SimpleTestCase):
    def test_health_returns_ok_without_login(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})