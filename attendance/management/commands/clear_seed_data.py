from django.core.management.base import BaseCommand

from attendance.models import (
    AbsenceJustification,
    AttendanceDay,
    Department,
    SystemLog,
    User,
    UserActivity,
    UserDailyLogin,
    UserSession,
)


class Command(BaseCommand):
    help = "Remove seeded data created by seed_data."

    def handle(self, *args, **options):
        usernames = [
            "superadmin",
            "admin1",
            "supervisor1",
            "supervisor2",
        ] + [f"employee{index}" for index in range(1, 21)]

        users_qs = User.objects.filter(username__in=usernames)

        AttendanceDay.objects.filter(user__in=users_qs).delete()
        AbsenceJustification.objects.filter(
            user__in=users_qs
        ).delete()
        AbsenceJustification.objects.filter(created_by__in=users_qs).delete()
        UserDailyLogin.objects.filter(user__in=users_qs).delete()
        UserSession.objects.filter(user__in=users_qs).delete()
        SystemLog.objects.filter(user__in=users_qs).delete()
        UserActivity.objects.filter(user__in=users_qs).delete()
        UserActivity.objects.filter(actor__in=users_qs).delete()

        deleted_users = users_qs.count()
        users_qs.delete()

        for code in ["HR", "FIN", "OPS", "IT", "SEC"]:
            dept = Department.objects.filter(code=code).first()
            if dept and not dept.user_set.exists():
                dept.delete()

        self.stdout.write(self.style.SUCCESS(f"Seeded users removed: {deleted_users}"))
