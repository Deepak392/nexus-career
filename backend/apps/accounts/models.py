from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        RECRUITER = "RECRUITER", "Recruiter"
        IPC_ADMIN = "IPC_ADMIN", "IPC Administrator"
        ALUMNI = "ALUMNI", "Alumni"
        SYSTEM_ADMIN = "SYSTEM_ADMIN", "System Administrator"

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
    )

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["role"], name="users_role_idx"),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"
