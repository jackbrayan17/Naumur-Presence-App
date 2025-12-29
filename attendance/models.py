from __future__ import annotations

from datetime import time

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import WORK_END_TIME, INTERN_END_TIME


class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
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
