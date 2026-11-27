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
    def setUp(self):
        self.recruiter = User.objects.create_user(
            username="public-opportunity-recruiter",
            email="public-recruiter@example.com",
            password="StrongPass123!secure",
            role=User.Role.RECRUITER,
        )
        self.company = Company.objects.create(
            name="Public Test Company",
            industry="Technology",
            contact_email="careers@public.example.com",
            verification_status=Company.VerificationStatus.VERIFIED,
        )
        RecruiterProfile.objects.create(user=self.recruiter, company=self.company)
        self.url = reverse("opportunity-list")

    def create_opportunity(self, **overrides):
        data = {
            "company": self.company,
            "created_by": self.recruiter,
            "title": "Published opportunity",
            "description": "Visible opportunity description with useful details.",
            "opportunity_type": Opportunity.OpportunityType.JOB,
            "required_skills": ["Python", "Django"],
            "work_mode": Opportunity.WorkMode.REMOTE,
            "location": "Chennai",
            "application_deadline": timezone.now() + timedelta(days=5),
            "status": Opportunity.Status.PUBLISHED,
            "published_at": timezone.now(),
        }
        data.update(overrides)
        return Opportunity.objects.create(**data)

    def test_public_endpoint_returns_only_published_unexpired_items(self):
        published = self.create_opportunity()
        self.create_opportunity(
            title="Draft opportunity",
            status=Opportunity.Status.DRAFT,
        )
        self.create_opportunity(
            title="Expired opportunity",
            application_deadline=timezone.now() - timedelta(days=1),
        )
        self.create_opportunity(
            title="Awaiting approval",
            status=Opportunity.Status.PENDING_APPROVAL,
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [published.pk])

    def test_public_search_matches_company_title_and_required_skills(self):
        python_item = self.create_opportunity(
            title="Platform Engineer",
            required_skills=["Python", "Django"],
        )
        self.create_opportunity(
            title="Frontend Engineer",
            required_skills=["React", "TypeScript"],
        )

        response = self.client.get(self.url, {"search": "Python"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [python_item.pk],
        )

        response = self.client.get(self.url, {"search": "Public Test"})
        self.assertEqual(response.data["count"], 2)

    def test_public_filters_by_type_mode_location_and_application_method(self):
        matching = self.create_opportunity(
            title="Remote internship",
            opportunity_type=Opportunity.OpportunityType.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            location="Chennai, India",
            application_method="EXTERNAL",
            external_application_url="https://jobs.example.com/apply",
        )
        self.create_opportunity(
            title="Onsite job",
            opportunity_type=Opportunity.OpportunityType.JOB,
            work_mode=Opportunity.WorkMode.ONSITE,
            location="Bengaluru",
        )

        response = self.client.get(
            self.url,
            {
                "opportunity_type": "INTERNSHIP",
                "work_mode": "REMOTE",
                "location": "chennai",
                "application_method": "EXTERNAL",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [matching.pk],
        )

    def test_public_ordering_supports_deadline_and_title(self):
        later = self.create_opportunity(
            title="Zeta Role",
            application_deadline=timezone.now() + timedelta(days=10),
        )
        sooner = self.create_opportunity(
            title="Alpha Role",
            application_deadline=timezone.now() + timedelta(days=2),
        )

        response = self.client.get(self.url, {"ordering": "deadline"})
        self.assertEqual(response.data["results"][0]["id"], sooner.pk)

        response = self.client.get(self.url, {"ordering": "title"})
        self.assertEqual(response.data["results"][0]["id"], sooner.pk)
        self.assertEqual(response.data["results"][1]["id"], later.pk)

    def test_public_detail_hides_non_published_opportunities(self):
        draft = self.create_opportunity(
            status=Opportunity.Status.DRAFT,
            title="Private draft",
        )
        response = self.client.get(reverse("opportunity-detail", args=[draft.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
