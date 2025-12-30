from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import attendance.models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0002_user_start_date_profile_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="AbsenceJustification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("medical", "Medical"),
                            ("funeral", "Funeral"),
                            ("personal", "Personal"),
                            ("official", "Official"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("other_reason", models.TextField(blank=True)),
                ("receipt", models.FileField(blank=True, null=True, upload_to=attendance.models.justification_upload_path)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_justifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="justifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-start_date", "user__last_name"],
            },
        ),
    ]
