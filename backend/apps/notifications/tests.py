from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Notification

User = get_user_model()


class NotificationAPITests(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="notification-owner",
            email="notification-owner@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username="notification-other",
            email="notification-other@example.com",
            password="StrongPass123!",
            role=User.Role.STUDENT,
        )
        self.own_notification = Notification.objects.create(
            recipient=self.student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application submitted",
            message="Your application was submitted successfully.",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application submitted",
            message="Another student's application notification.",
        )

    def test_student_only_sees_own_notifications(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.own_notification.pk)

    def test_student_can_mark_own_notification_read(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            reverse("notification-mark-read", args=[self.own_notification.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own_notification.refresh_from_db()
        self.assertIsNotNone(self.own_notification.read_at)

    def test_student_cannot_mark_another_users_notification_read(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            reverse("notification-mark-read", args=[self.other_notification.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_notification.refresh_from_db()
        self.assertIsNone(self.other_notification.read_at)

    def test_alumni_only_sees_own_referral_notifications(self):
        alumni = User.objects.create_user(
            username="notification-alumni",
            email="notification-alumni@example.com",
            password="StrongPass123!",
            role=User.Role.ALUMNI,
        )
        other_alumni = User.objects.create_user(
            username="notification-alumni-other",
            email="notification-alumni-other@example.com",
            password="StrongPass123!",
            role=User.Role.ALUMNI,
        )
        own = Notification.objects.create(
            recipient=alumni,
            notification_type="REFERRAL_REQUEST",
            title="New referral request",
            message="A student requested a referral.",
        )
        Notification.objects.create(
            recipient=other_alumni,
            notification_type="REFERRAL_REQUEST",
            title="New referral request",
            message="Another student requested a referral.",
        )
        self.client.force_authenticate(user=alumni)
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], own.pk)
        self.assertIsNone(response.data["results"][0]["referral_request_id"])
