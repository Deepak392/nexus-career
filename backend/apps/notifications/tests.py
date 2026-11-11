from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from api.core import events
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

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

    def test_duplicate_notification_is_not_created(self):
        notification_data = {
            "recipient": self.student,
            "notification_type": Notification.NotificationType.APPLICATION_SUBMITTED,
            "title": "Application submitted",
            "message": "Your application was submitted successfully.",
            "deduplication_key": "application:100:submitted",
        }

        first, first_created = create_notification(**notification_data)
        second, second_created = create_notification(**notification_data)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Notification.objects.filter(
                deduplication_key="application:100:submitted"
            ).count(),
            1,
        )

    def test_different_deduplication_keys_create_separate_notifications(self):
        first, first_created = create_notification(
            recipient=self.student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application submitted",
            message="First application submitted.",
            deduplication_key="application:100:submitted",
        )

        second, second_created = create_notification(
            recipient=self.student,
            notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
            title="Application submitted",
            message="Second application submitted.",
            deduplication_key="application:101:submitted",
        )

        self.assertTrue(first_created)
        self.assertTrue(second_created)
        self.assertNotEqual(first.pk, second.pk)
    def test_replayed_event_creates_only_one_notification(self):
        def notification_handler(payload):
            create_notification(
                recipient=self.student,
                notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
                title="Application submitted",
                message="Your application was submitted successfully.",
                deduplication_key=payload["deduplication_key"],
            )

        events.register_handler(
            "test.notification.replay",
            notification_handler,
        )

        payload = {
            "deduplication_key": "application:replay-test:submitted",
        }

        events.emit("test.notification.replay", payload)
        events.emit("test.notification.replay", payload)

        self.assertEqual(
            Notification.objects.filter(
                deduplication_key="application:replay-test:submitted"
            ).count(),
            1,
        )
