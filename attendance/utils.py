from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional

from django.utils import timezone


WORK_START_TIME = time(8, 30)
WORK_END_TIME = time(17, 30)
INTERN_END_TIME = time(16, 30)


def get_week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def get_week_days(week_start: date) -> list[date]:
    return [week_start + timedelta(days=offset) for offset in range(7)]


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def working_days_between(start: date, end: date) -> int:
    count = 0
    for day in date_range(start, end):
        if day.weekday() < 5:
            count += 1
    return count


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def parse_time_or_default(value: Optional[str], default: time) -> time:
    if value:
        try:
            parsed = datetime.strptime(value, "%H:%M").time()
            return parsed
        except ValueError:
            return default
    return default


def week_label(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    return f"{week_start.isoformat()} to {week_end.isoformat()}"


def now_local_time() -> time:
    return timezone.localtime().time()


def hours_between(start_time: time, end_time: time) -> float:
    start_dt = datetime.combine(date.today(), start_time)
    end_dt = datetime.combine(date.today(), end_time)
    delta = end_dt - start_dt
    return max(delta.total_seconds() / 3600, 0)


def expected_daily_hours(is_intern: bool) -> float:
    end_time = INTERN_END_TIME if is_intern else WORK_END_TIME
    return hours_between(WORK_START_TIME, end_time)
