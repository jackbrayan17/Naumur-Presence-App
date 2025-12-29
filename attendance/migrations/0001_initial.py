from django.conf import settings
from django.contrib.auth.models import UserManager
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                (
                    "role",
                    models.CharField(
                        choices=[("admin", "Admin"), ("supervisor", "Supervisor"), ("employee", "Employee")],
                        default="employee",
                        max_length=20,
                    ),
                ),
                ("is_intern", models.BooleanField(default=False)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="attendance.department",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[
                ("objects", UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="AttendanceDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("arrival_time", models.TimeField(blank=True, null=True)),
                ("departure_time", models.TimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendances", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verified_attendances",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-date", "user__last_name", "user__first_name"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "date"), name="unique_attendance_day")
                ],
            },
        ),
        migrations.CreateModel(
            name="SystemLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=50)),
                ("message", models.TextField()),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserDailyLogin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("first_login_at", models.DateTimeField(blank=True, null=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("last_ip", models.CharField(blank=True, max_length=64)),
                ("online", models.BooleanField(default=False)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_logins", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-date", "user__last_name", "user__first_name"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "date"), name="unique_daily_login")
                ],
            },
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(db_index=True, max_length=100)),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("login_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("logout_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-login_at"],
            },
        ),
    ]
