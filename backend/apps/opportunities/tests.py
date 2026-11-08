from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.opportunities.models import Opportunity
from apps.recruiters.models import Company, RecruiterProfile

User = get_user_model()


class PublicOpportunityDiscoveryTests(APITestCase):
    def test_public_endpoint_returns_only_published_unexpired_items(self):
        recruiter = User.objects.create_user(
            username="public-opportunity-recruiter",
            email="public-recruiter@example.com",
            password="StrongPass123!secure",
            role=User.Role.RECRUITER,
        )
        company = Company.objects.create(
            name="Public Test Company",
            industry="Technology",
            contact_email="careers@public.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=recruiter, company=company)
        published = Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="Published opportunity",
            description="Visible opportunity description.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            application_deadline=timezone.now() + timedelta(days=5),
            status=Opportunity.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        Opportunity.objects.create(
            company=company,
            created_by=recruiter,
            title="Draft opportunity",
            description="Draft opportunity description.",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Remote",
            application_deadline=timezone.now() + timedelta(days=5),
            status=Opportunity.Status.DRAFT,
        )
        response = self.client.get(reverse("opportunity-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(published.pk, ids)
