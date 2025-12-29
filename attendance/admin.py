from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AttendanceDay,
    Department,
    SystemLog,
    User,
    UserDailyLogin,
    UserSession,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Role and Department",
            {"fields": ("role", "department", "is_intern")},
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            "Role and Department",
            {"fields": ("role", "department", "is_intern")},
        ),
    )
    list_display = (
        "username",
        "first_name",
        "last_name",
        "role",
        "department",
        "is_intern",
        "is_staff",
    )
    list_filter = ("role", "department", "is_intern")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


@admin.register(AttendanceDay)
class AttendanceDayAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "arrival_time",
        "departure_time",
        "verified_by",
        "verified_at",
    )
    list_filter = ("date", "user__department")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "session_key",
        "ip_address",
        "login_at",
        "last_seen_at",
        "logout_at",
        "is_active",
    )
    list_filter = ("is_active", "login_at")
    search_fields = ("user__username", "session_key")


@admin.register(UserDailyLogin)
class UserDailyLoginAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "date",
        "first_login_at",
        "last_login_at",
        "last_seen_at",
        "last_ip",
        "online",
    )
    list_filter = ("online", "date")
    search_fields = ("user__username",)


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "ip_address", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("message", "user__username")
