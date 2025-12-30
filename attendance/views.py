from __future__ import annotations

import csv
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from django.utils.translation import gettext as _

from openpyxl import Workbook

from .forms import (
    AbsenceJustificationForm,
    DepartmentCreateForm,
    EmployeeCreateForm,
    LoginForm,
    ProfileImageForm,
)
from .models import AttendanceDay, Department, SystemLog, User, UserDailyLogin
from .utils import (
    WORK_START_TIME,
    expected_daily_hours,
    get_client_ip,
    get_week_days,
    get_week_start,
    hours_between,
    now_local_time,
    parse_date,
    parse_time_or_default,
    week_label,
    working_days_between,
)


def _log_event(request, event_type: str, message: str, meta: dict | None = None) -> None:
    SystemLog.objects.create(
        event_type=event_type,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request),
        message=message,
        meta=meta or {},
    )


def _build_week_matrix(week_start_date):
    week_days = get_week_days(week_start_date)
    week_end = week_start_date + timedelta(days=6)
    departments = list(Department.objects.all())
    dept_tables = []
    dept_map = {}
    for dept in departments:
        table = {"department": dept, "label": dept.name, "rows": []}
        dept_tables.append(table)
        dept_map[dept.id] = table

    unassigned_table = {"department": None, "label": _("Unassigned"), "rows": []}

    employees = list(
        User.objects.filter(role=User.Roles.EMPLOYEE)
        .select_related("department")
        .order_by("department__name", "last_name", "first_name")
    )
    records = AttendanceDay.objects.filter(
        user__in=employees, date__range=(week_start_date, week_end)
    ).select_related("verified_by")
    record_map = {(record.user_id, record.date): record for record in records}

    for employee in employees:
        table = dept_map.get(employee.department_id, unassigned_table)
        row = {"employee": employee, "cells": []}
        for day in week_days:
            record = record_map.get((employee.id, day))
            row["cells"].append(
                {
                    "date": day,
                    "arrival": record.arrival_time if record else None,
                    "departure": record.departure_time if record else None,
                    "verified_by": record.verified_by if record else None,
                    "verified_at": record.verified_at if record else None,
                    "is_verified": bool(record and record.verified_by_id),
                }
            )
        table["rows"].append(row)

    if unassigned_table["rows"]:
        dept_tables.append(unassigned_table)

    return week_days, dept_tables


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
            return redirect("home")
    else:
        form = LoginForm(request)
    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    user = request.user
    if request.method == "POST":
        form = ProfileImageForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            updated_user.save(update_fields=["profile_image"])
            messages.success(request, _("Profile picture updated."))
            return redirect("profile")
    else:
        form = ProfileImageForm(instance=user)

    return render(request, "profile.html", {"form": form})


@login_required
def home(request):
    if request.user.is_admin:
        return redirect("admin_dashboard")
    if request.user.is_supervisor:
        return redirect("supervisor_verify")
    return redirect("employee_week")


@login_required
def employee_week(request):
    viewer = request.user
    target_id = request.GET.get("user") or request.POST.get("user_id")
    target_user = viewer
    if target_id:
        if viewer.is_admin or viewer.is_supervisor:
            try:
                target_user = User.objects.get(id=target_id)
            except User.DoesNotExist:
                messages.error(request, _("Employee not found."))
                return redirect("admin_dashboard")
        else:
            return HttpResponseForbidden(_("Access denied."))

    today = timezone.localdate()
    week_start = parse_date(request.GET.get("week")) or get_week_start(today)
    week_days = get_week_days(week_start)
    week_end = week_start + timedelta(days=6)

    attendance_qs = AttendanceDay.objects.filter(
        user=target_user, date__range=(week_start, week_end)
    )
    attendance_map = {record.date: record for record in attendance_qs}

    is_self_employee = viewer == target_user and viewer.role == User.Roles.EMPLOYEE

    if request.method == "POST":
        save_day = parse_date(request.POST.get("save_day"))
        if not save_day or save_day not in week_days:
            messages.error(request, _("Select a valid day to save."))
            return redirect(f"{request.path}?week={week_start.isoformat()}")
        if save_day < target_user.start_date:
            messages.error(request, _("This day is before the employee start date."))
            return redirect(f"{request.path}?week={week_start.isoformat()}")
        if is_self_employee and save_day != today:
            messages.error(request, _("Only today can be submitted."))
            return redirect(f"{request.path}?week={week_start.isoformat()}")

        changes = 0
        for day in [save_day]:
            attendance = attendance_map.get(day)
            if not attendance:
                attendance = AttendanceDay(user=target_user, date=day)

            changed = False
            arrive_key = f"arrive_{day.isoformat()}"
            depart_key = f"depart_{day.isoformat()}"

            if request.POST.get(arrive_key) == "on":
                if (
                    attendance.arrival_time is None
                    or viewer.is_admin
                    or viewer.is_supervisor
                ):
                    arrival_time = parse_time_or_default(
                        request.POST.get(f"arrive_time_{day.isoformat()}"),
                        WORK_START_TIME,
                    )
                    attendance.arrival_time = arrival_time
                    changed = True
                else:
                    messages.warning(
                        request,
                        _(
                            "Arrival already recorded. Ask a supervisor or admin to edit."
                        ),
                    )

            if request.POST.get(depart_key) == "on":
                if attendance.arrival_time is None and not (viewer.is_admin or viewer.is_supervisor):
                    messages.error(
                        request,
                        _(
                            "Departure requires an arrival time. Ask a supervisor or admin."
                        ),
                    )
                elif (
                    attendance.departure_time is None
                    or viewer.is_admin
                    or viewer.is_supervisor
                ):
                    departure_time = parse_time_or_default(
                        request.POST.get(f"depart_time_{day.isoformat()}"),
                        target_user.expected_end_time(),
                    )
                    attendance.departure_time = departure_time
                    changed = True

            if changed:
                attendance.save()
                attendance_map[day] = attendance
                changes += 1

        if changes:
            _log_event(
                request,
                SystemLog.EVENT_ATTENDANCE,
                f"Attendance updated by {viewer.username}",
                {
                    "week_start": week_start.isoformat(),
                    "changes": changes,
                    "employee": target_user.username,
                    "day": save_day.isoformat(),
                },
            )
            messages.success(request, _("Attendance saved."))
        else:
            messages.info(request, _("No changes to save for this day."))
        query = f"week={week_start.isoformat()}"
        if target_user != viewer:
            query += f"&user={target_user.id}"
        return redirect(f"{request.path}?{query}")

    effective_end = min(week_end, today)
    effective_start = max(week_start, target_user.start_date)
    present_days = sum(
        1
        for record in attendance_map.values()
        if record.arrival_time is not None
        and effective_start <= record.date <= effective_end
    )
    expected_days = (
        working_days_between(effective_start, effective_end)
        if effective_start <= effective_end
        else 0
    )
    absent_days = max(expected_days - present_days, 0)

    present_hours = 0.0
    for record in attendance_map.values():
        if (
            record.arrival_time
            and record.departure_time
            and effective_start <= record.date <= effective_end
        ):
            present_hours += hours_between(record.arrival_time, record.departure_time)
    expected_hours = expected_daily_hours(target_user.is_intern) * expected_days
    absent_hours = max(expected_hours - present_hours, 0)

    week_rows = []
    for day in week_days:
        record = attendance_map.get(day)
        is_before_start = day < target_user.start_date
        if is_self_employee:
            can_edit_arrival = day == today and (
                record is None or record.arrival_time is None
            )
            can_edit_departure = day == today and (
                record is None or record.departure_time is None
            )
        else:
            can_edit_arrival = day <= today and (
                record is None
                or record.arrival_time is None
                or viewer.is_admin
                or viewer.is_supervisor
            )
            can_edit_departure = day <= today and (
                record is None
                or record.departure_time is None
                or viewer.is_admin
                or viewer.is_supervisor
            )
        if is_before_start:
            can_edit_arrival = False
            can_edit_departure = False
        is_locked = is_before_start or day > today or (is_self_employee and day != today)
        week_rows.append(
            {
                "date": day,
                "record": record,
                "can_edit_arrival": can_edit_arrival,
                "can_edit_departure": can_edit_departure,
                "is_future": day > today,
                "is_before_start": is_before_start,
                "is_locked": is_locked,
            }
        )

    context = {
        "week_start": week_start,
        "week_end": week_end,
        "prev_week": week_start - timedelta(days=7),
        "next_week": week_start + timedelta(days=7),
        "week_rows": week_rows,
        "today": today,
        "present_days": present_days,
        "absent_days": absent_days,
        "present_hours": present_hours,
        "absent_hours": absent_hours,
        "expected_hours": expected_hours,
        "default_departure_time": target_user.expected_end_time(),
        "target_user": target_user,
        "is_editing_other": target_user != viewer,
        "is_self_employee": is_self_employee,
    }
    return render(request, "employee_week.html", context)


@login_required
def supervisor_verify(request):
    user = request.user
    if not (user.is_admin or user.is_supervisor):
        return HttpResponseForbidden(_("Access denied."))

    today = timezone.localdate()
    supervisor_record, _ = AttendanceDay.objects.get_or_create(user=user, date=today)

    employee_form = EmployeeCreateForm()
    department_form = DepartmentCreateForm()
    justification_form = AbsenceJustificationForm()

    if request.method == "POST" and "create_department" in request.POST:
        department_form = DepartmentCreateForm(request.POST)
        if department_form.is_valid():
            department_form.save()
            messages.success(request, _("Department created."))
            return redirect("supervisor_verify")
    elif request.method == "POST" and "create_employee" in request.POST:
        employee_form = EmployeeCreateForm(request.POST)
        if employee_form.is_valid():
            employee_form.save()
            messages.success(request, _("Employee created."))
            return redirect("supervisor_verify")
    elif request.method == "POST" and "create_justification" in request.POST:
        justification_form = AbsenceJustificationForm(request.POST, request.FILES)
        if justification_form.is_valid():
            justification = justification_form.save(commit=False)
            justification.created_by = user
            justification.save()
            _log_event(
                request,
                SystemLog.EVENT_JUSTIFICATION,
                f"Justification added by {user.username}",
                {"employee": justification.user.username},
            )
            messages.success(request, _("Justification saved."))
            return redirect("supervisor_verify")

    if request.method == "POST" and "check_in" in request.POST:
        if supervisor_record.arrival_time is None:
            supervisor_record.arrival_time = now_local_time()
            supervisor_record.save(update_fields=["arrival_time"])
            _log_event(
                request,
                SystemLog.EVENT_ATTENDANCE,
                f"Supervisor {user.username} checked in",
                {"date": today.isoformat()},
            )
        return redirect("supervisor_verify")

    if supervisor_record.arrival_time is None:
        return render(
            request,
            "supervisor_verify.html",
            {
                "needs_checkin": True,
                "today": today,
                "employee_form": employee_form,
                "department_form": department_form,
                "justification_form": justification_form,
            },
        )

    if request.method == "POST" and "verify_selected" in request.POST:
        ids = request.POST.getlist("verify_ids")
        verified = 0
        for record in AttendanceDay.objects.filter(id__in=ids, verified_by__isnull=True):
            record.verified_by = user
            record.verified_at = timezone.now()
            record.save(update_fields=["verified_by", "verified_at"])
            verified += 1

        if verified:
            _log_event(
                request,
                SystemLog.EVENT_VERIFY,
                f"Supervisor {user.username} verified {verified} employees",
                {"date": today.isoformat(), "count": verified},
            )
            messages.success(
                request, _("Verified %(count)s employees.") % {"count": verified}
            )
        return redirect("supervisor_verify")

    if request.method == "POST" and "depart_self" in request.POST:
        if supervisor_record.departure_time is None:
            supervisor_record.departure_time = now_local_time()
            supervisor_record.save(update_fields=["departure_time"])
            _log_event(
                request,
                SystemLog.EVENT_ATTENDANCE,
                f"Supervisor {user.username} checked out",
                {"date": today.isoformat()},
            )
        return redirect("supervisor_verify")

    pending_qs = AttendanceDay.objects.filter(
        date=today,
        arrival_time__isnull=False,
        verified_by__isnull=True,
        user__role=User.Roles.EMPLOYEE,
    ).select_related("user", "user__department")

    employees = (
        User.objects.filter(role=User.Roles.EMPLOYEE)
        .select_related("department")
        .order_by("department__name", "last_name", "first_name")
    )

    context = {
        "needs_checkin": False,
        "today": today,
        "pending_attendance": pending_qs,
        "supervisor_record": supervisor_record,
        "employees": employees,
        "current_week_start": get_week_start(today),
        "employee_form": employee_form,
        "department_form": department_form,
        "justification_form": justification_form,
    }
    return render(request, "supervisor_verify.html", context)


@login_required
def admin_dashboard(request):
    user = request.user
    if not user.is_admin:
        return HttpResponseForbidden(_("Access denied."))

    today = timezone.localdate()
    start_date = parse_date(request.GET.get("start")) or (today - timedelta(days=30))
    end_date = parse_date(request.GET.get("end")) or today

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    departments = Department.objects.all()
    employees = User.objects.filter(role=User.Roles.EMPLOYEE)
    effective_end = min(end_date, today)

    dept_rows = []
    for dept in departments:
        dept_employees = list(employees.filter(department=dept))
        expected = 0
        for employee in dept_employees:
            employee_start = max(start_date, employee.start_date)
            if employee_start <= effective_end:
                expected += working_days_between(employee_start, effective_end)
        present = AttendanceDay.objects.filter(
            user__in=dept_employees,
            date__range=(start_date, effective_end),
            arrival_time__isnull=False,
        ).count()
        rate = (present / expected * 100) if expected else 0
        dept_rows.append(
            {
                "department": dept,
                "expected": expected,
                "present": present,
                "rate": rate,
            }
        )

    daily_logins = {
        record.user_id: record.online
        for record in UserDailyLogin.objects.filter(date=today)
    }

    employee_rows = []
    employee_cards = []
    for employee in employees.select_related("department"):
        employee_start = max(start_date, employee.start_date)
        records = list(
            AttendanceDay.objects.filter(
                user=employee, date__range=(employee_start, effective_end)
            )
        )
        present_days = sum(1 for record in records if record.arrival_time is not None)
        present_hours = sum(
            hours_between(record.arrival_time, record.departure_time)
            for record in records
            if record.arrival_time and record.departure_time
        )
        employee_expected_days = (
            working_days_between(employee_start, effective_end)
            if employee_start <= effective_end
            else 0
        )
        expected_hours = expected_daily_hours(employee.is_intern) * employee_expected_days
        absent_hours = max(expected_hours - present_hours, 0)
        absent_days = max(employee_expected_days - present_days, 0)
        employee_rows.append(
            {
                "employee": employee,
                "department": employee.department,
                "present_days": present_days,
                "absent_days": absent_days,
                "present_hours": present_hours,
                "absent_hours": absent_hours,
            }
        )

        total_start = employee.start_date
        total_end = today
        total_working_days = (
            working_days_between(total_start, total_end)
            if total_start <= total_end
            else 0
        )
        total_records = list(
            AttendanceDay.objects.filter(
                user=employee, date__range=(total_start, total_end)
            )
        )
        total_present_days = sum(
            1 for record in total_records if record.arrival_time is not None
        )
        total_present_hours = sum(
            hours_between(record.arrival_time, record.departure_time)
            for record in total_records
            if record.arrival_time and record.departure_time
        )
        total_expected_hours = expected_daily_hours(employee.is_intern) * total_working_days
        total_absent_hours = max(total_expected_hours - total_present_hours, 0)
        total_absent_days = max(total_working_days - total_present_days, 0)

        employee_cards.append(
            {
                "employee": employee,
                "start_date": employee.start_date,
                "status": _("Online") if daily_logins.get(employee.id) else _("Offline"),
                "present_hours": total_present_hours,
                "absent_hours": total_absent_hours,
                "absent_days": total_absent_days,
            }
        )

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "dept_rows": dept_rows,
        "employee_rows": employee_rows,
        "current_week_start": get_week_start(timezone.localdate()),
        "employee_cards": employee_cards,
    }
    return render(request, "admin_dashboard.html", context)


@login_required
def history(request):
    user = request.user
    if not (user.is_admin or user.is_supervisor):
        return HttpResponseForbidden(_("Access denied."))

    today = timezone.localdate()
    start_date = parse_date(request.GET.get("start")) or (today - timedelta(days=90))
    end_date = parse_date(request.GET.get("end")) or today
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    week_start = get_week_start(start_date)
    weeks = []
    while week_start <= end_date:
        weeks.append(
            {
                "start": week_start,
                "end": week_start + timedelta(days=6),
                "label": week_label(week_start),
            }
        )
        week_start += timedelta(days=7)

    paginator = Paginator(weeks, 10)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "page": page,
    }
    return render(request, "history.html", context)


@login_required
def history_week(request, week_start: str):
    user = request.user
    if not (user.is_admin or user.is_supervisor):
        return HttpResponseForbidden(_("Access denied."))

    week_start_date = parse_date(week_start)
    if not week_start_date:
        return HttpResponse(_("Invalid week start."), status=400)

    week_days, dept_tables = _build_week_matrix(week_start_date)
    context = {
        "week_start": week_start_date,
        "week_end": week_start_date + timedelta(days=6),
        "week_days": week_days,
        "dept_tables": dept_tables,
    }
    return render(request, "history_week.html", context)


@login_required
def history_export(request, week_start: str, fmt: str):
    user = request.user
    if not (user.is_admin or user.is_supervisor):
        return HttpResponseForbidden(_("Access denied."))

    week_start_date = parse_date(week_start)
    if not week_start_date:
        return HttpResponse(_("Invalid week start."), status=400)

    week_days, dept_tables = _build_week_matrix(week_start_date)

    if fmt == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="attendance_{week_start_date.isoformat()}.csv"'
        )
        writer = csv.writer(response)
        header = ["Department", "Employee"]
        for day in week_days:
            label = day.isoformat()
            header.extend(
                [
                    f"{label} Arrival",
                    f"{label} Departure",
                    f"{label} Verified By",
                    f"{label} Verified At",
                ]
            )
        writer.writerow(header)
        for table in dept_tables:
            for row in table["rows"]:
                values = [
                    table["label"],
                    row["employee"].get_full_name() or row["employee"].username,
                ]
                for cell in row["cells"]:
                    values.extend(
                        [
                            cell["arrival"].strftime("%H:%M") if cell["arrival"] else "",
                            cell["departure"].strftime("%H:%M")
                            if cell["departure"]
                            else "",
                            cell["verified_by"].get_full_name()
                            if cell["verified_by"]
                            else "",
                            cell["verified_at"].strftime("%Y-%m-%d %H:%M")
                            if cell["verified_at"]
                            else "",
                        ]
                    )
                writer.writerow(values)

        _log_event(
            request,
            SystemLog.EVENT_EXPORT,
            f"Weekly CSV exported by {user.username}",
            {"week_start": week_start_date.isoformat()},
        )
        return response

    if fmt == "xlsx":
        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        header = ["Employee"]
        for day in week_days:
            label = day.isoformat()
            header.extend(
                [
                    f"{label} Arrival",
                    f"{label} Departure",
                    f"{label} Verified By",
                    f"{label} Verified At",
                ]
            )
        for table in dept_tables:
            sheet_name = table["label"][:31]
            sheet = workbook.create_sheet(title=sheet_name)
            sheet.append(header)
            for row in table["rows"]:
                values = [row["employee"].get_full_name() or row["employee"].username]
                for cell in row["cells"]:
                    values.extend(
                        [
                            cell["arrival"].strftime("%H:%M")
                            if cell["arrival"]
                            else "",
                            cell["departure"].strftime("%H:%M")
                            if cell["departure"]
                            else "",
                            cell["verified_by"].get_full_name()
                            if cell["verified_by"]
                            else "",
                            cell["verified_at"].strftime("%Y-%m-%d %H:%M")
                            if cell["verified_at"]
                            else "",
                        ]
                    )
                sheet.append(values)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response[
            "Content-Disposition"
        ] = f'attachment; filename="attendance_{week_start_date.isoformat()}.xlsx"'
        workbook.save(response)

        _log_event(
            request,
            SystemLog.EVENT_EXPORT,
            f"Weekly XLSX exported by {user.username}",
            {"week_start": week_start_date.isoformat()},
        )
        return response

    return HttpResponse(_("Format not supported."), status=400)
