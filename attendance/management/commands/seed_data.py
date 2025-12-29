import random
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from attendance.models import AttendanceDay, Department, User
from attendance.utils import INTERN_END_TIME, WORK_END_TIME, WORK_START_TIME


class Command(BaseCommand):
    help = "Seed departments, users, and attendance data."

    def handle(self, *args, **options):
        departments = [
            ("HR", "Human Resources"),
            ("FIN", "Finance"),
            ("OPS", "Operations"),
            ("IT", "Information Technology"),
            ("SEC", "Security"),
        ]

        dept_objs = []
        for code, name in departments:
            dept, _ = Department.objects.get_or_create(code=code, defaults={"name": name})
            dept.name = name
            dept.save(update_fields=["name"])
            dept_objs.append(dept)

        if not User.objects.filter(username="superadmin").exists():
            User.objects.create_superuser(
                username="superadmin",
                password="SuperAdmin123!",
                role=User.Roles.ADMIN,
            )

        if not User.objects.filter(username="admin1").exists():
            User.objects.create_user(
                username="admin1",
                password="Admin123!",
                role=User.Roles.ADMIN,
                is_staff=True,
                first_name="Arlette",
                last_name="Nkoum",
                department=dept_objs[0],
            )

        supervisors = []
        for username, first_name, last_name, dept in [
            ("supervisor1", "Blaise", "Ekani", dept_objs[2]),
            ("supervisor2", "Carine", "Mballa", dept_objs[4]),
        ]:
            if not User.objects.filter(username=username).exists():
                supervisor = User.objects.create_user(
                    username=username,
                    password="Supervisor123!",
                    role=User.Roles.SUPERVISOR,
                    is_staff=True,
                    first_name=first_name,
                    last_name=last_name,
                    department=dept,
                )
            else:
                supervisor = User.objects.get(username=username)
            supervisors.append(supervisor)

        employees_data = [
            ("Jean", "Mballa"),
            ("Sylvie", "Ngono"),
            ("Patrick", "Fokou"),
            ("Brigitte", "Biloa"),
            ("Eric", "Manga"),
            ("Fanny", "Ndom"),
            ("Denis", "Etoa"),
            ("Nadine", "Tchoua"),
            ("Arnaud", "Kouame"),
            ("Josiane", "Mpacko"),
            ("Roland", "Simo"),
            ("Carole", "Njoya"),
            ("Cedric", "Ngapna"),
            ("Alain", "Nzi"),
            ("Lydie", "Bikoi"),
            ("Serge", "Nkong"),
            ("Flora", "Ekane"),
            ("Emile", "Fouda"),
            ("Aicha", "Ngo"), 
            ("Luc", "Ngassa"),
        ]

        employees = []
        for index, (first_name, last_name) in enumerate(employees_data):
            username = f"employee{index + 1}"
            if User.objects.filter(username=username).exists():
                employee = User.objects.get(username=username)
            else:
                employee = User.objects.create_user(
                    username=username,
                    password="Employee123!",
                    role=User.Roles.EMPLOYEE,
                    first_name=first_name,
                    last_name=last_name,
                    department=dept_objs[index % len(dept_objs)],
                )
            employees.append(employee)

        for index, employee in enumerate(employees):
            employee.is_intern = index % 5 == 0
            employee.save(update_fields=["is_intern"])

        start_date = date(2026, 1, 1)
        end_date = date(2026, 2, 28)
        rng = random.Random(42)

        for day_offset in range((end_date - start_date).days + 1):
            current_day = start_date + timedelta(days=day_offset)
            if current_day.weekday() >= 5:
                continue
            for employee in employees:
                if rng.random() < 0.15:
                    continue

                attendance, _ = AttendanceDay.objects.get_or_create(
                    user=employee, date=current_day
                )
                start_minute = rng.randint(0, 20)
                attendance.arrival_time = time_with_offset(WORK_START_TIME, start_minute)

                end_time = INTERN_END_TIME if employee.is_intern else WORK_END_TIME
                end_minute = rng.randint(-10, 10)
                attendance.departure_time = time_with_offset(end_time, end_minute)

                if rng.random() < 0.7 and supervisors:
                    supervisor = rng.choice(supervisors)
                    attendance.verified_by = supervisor
                    attendance.verified_at = timezone.make_aware(
                        datetime.combine(current_day, time_with_offset(WORK_START_TIME, 60))
                    )
                attendance.save()

        self.stdout.write(self.style.SUCCESS("Seed data created."))


def time_with_offset(base_time, minutes_offset):
    full_datetime = datetime.combine(date.today(), base_time) + timedelta(
        minutes=minutes_offset
    )
    return full_datetime.time()
