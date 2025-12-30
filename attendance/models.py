from __future__ import annotations

from datetime import time

from django.contrib.auth.models import AbstractUser
from django.db import models
from pathlib import Path

from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .utils import WORK_END_TIME, INTERN_END_TIME


class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", _("Admin")
        SUPERVISOR = "supervisor", _("Supervisor")
        EMPLOYEE = "employee", _("Employee")

    role = models.CharField(
        max_length=20, choices=Roles.choices, default=Roles.EMPLOYEE
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_intern = models.BooleanField(default=False)
    start_date = models.DateField(default=timezone.localdate)
    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_admin(self) -> bool:
        return self.is_superuser or self.role == self.Roles.ADMIN

    @property
    def is_supervisor(self) -> bool:
        return self.is_superuser or self.role == self.Roles.SUPERVISOR

    @property
    def is_employee(self) -> bool:
        return self.is_superuser or self.role == self.Roles.EMPLOYEE

    def expected_end_time(self) -> time:
        return INTERN_END_TIME if self.is_intern else WORK_END_TIME

    def initials(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        parts = [part for part in full_name.split() if part]
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (self.username or "U")[:2].upper()

    def avatar_color(self) -> str:
        palette = [
            "#6F3CFF",
            "#9C5BFF",
            "#F05CFF",
            "#24B47E",
            "#FF7A59",
            "#1F8EFA",
            "#F2C94C",
            "#5E60CE",
        ]
        seed = f"{self.username}{self.first_name}{self.last_name}"
        total = sum(ord(char) for char in seed) if seed else 0
        return palette[total % len(palette)]


def justification_upload_path(instance, filename: str) -> str:
    safe_name = slugify(
        instance.user.get_full_name() or instance.user.username or "user"
    ) or "user"
    start = instance.start_date.isoformat()
    end = instance.end_date.isoformat()
    period = f"{start}_to_{end}"
    safe_file = Path(filename).name
    return f"justifications/{safe_name}/{period}/{safe_file}"


class AbsenceJustification(models.Model):
    class Reasons(models.TextChoices):
        MEDICAL = "medical", _("Medical")
        FUNERAL = "funeral", _("Funeral")
        PERSONAL = "personal", _("Personal")
        OFFICIAL = "official", _("Official")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="justifications"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_justifications"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=20, choices=Reasons.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_justifications",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_note = models.TextField(blank=True)
    other_reason = models.TextField(blank=True)
    receipt = models.FileField(upload_to=justification_upload_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "user__last_name"]

    def __str__(self) -> str:
        return f"{self.user} - {self.start_date.isoformat()} to {self.end_date.isoformat()}"


class AttendanceDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendances")
    date = models.DateField()
    arrival_time = models.TimeField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_attendances",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_attendance_day")
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.date.isoformat()}"

    @property
    def is_present(self) -> bool:
        return self.arrival_time is not None

    @property
    def is_verified(self) -> bool:
        return self.verified_by is not None


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=100, db_index=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    login_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-login_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.session_key}"


class UserDailyLogin(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_logins")
    date = models.DateField()
    first_login_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_ip = models.CharField(max_length=64, blank=True)
    online = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "user__last_name", "user__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_daily_login")
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.date.isoformat()}"


class SystemLog(models.Model):
    EVENT_LOGIN = "login"
    EVENT_LOGOUT = "logout"
    EVENT_ATTENDANCE = "attendance"
    EVENT_VERIFY = "verify"
    EVENT_EXPORT = "export"
    EVENT_BACKUP = "backup"
    EVENT_JUSTIFICATION = "justification"

    event_type = models.CharField(max_length=50)
    message = models.TextField()
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs"
    )
    ip_address = models.CharField(max_length=64, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} - {self.created_at.isoformat()}"
