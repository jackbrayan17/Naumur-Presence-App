from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import SystemLog, UserActivity, UserDailyLogin, UserSession
from .utils import get_client_ip


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    request.session.save()
    session_key = request.session.session_key or ""
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    now = timezone.now()

    if session_key:
        UserSession.objects.update_or_create(
            user=user,
            session_key=session_key,
            defaults={
                "ip_address": ip_address,
                "user_agent": user_agent,
                "login_at": now,
                "last_seen_at": now,
                "logout_at": None,
                "is_active": True,
            },
        )

    today = timezone.localdate()
    daily, created = UserDailyLogin.objects.get_or_create(user=user, date=today)
    if created or daily.first_login_at is None:
        daily.first_login_at = now
    daily.last_login_at = now
    daily.last_seen_at = now
    daily.last_ip = ip_address
    daily.online = True
    daily.save(update_fields=["first_login_at", "last_login_at", "last_seen_at", "last_ip", "online"])

    SystemLog.objects.create(
        event_type=SystemLog.EVENT_LOGIN,
        user=user,
        ip_address=ip_address,
        message=f"User {user.username} logged in",
        meta={"session_key": session_key},
    )
    UserActivity.objects.create(
        user=user,
        actor=user,
        event_type="login",
        message="User logged in.",
        meta={"session_key": session_key},
    )


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):
    now = timezone.now()
    session_key = request.session.session_key or ""
    ip_address = get_client_ip(request)

    if session_key:
        UserSession.objects.filter(
            user=user, session_key=session_key, is_active=True
        ).update(is_active=False, logout_at=now)

    today = timezone.localdate()
    UserDailyLogin.objects.filter(user=user, date=today).update(online=False)

    SystemLog.objects.create(
        event_type=SystemLog.EVENT_LOGOUT,
        user=user,
        ip_address=ip_address,
        message=f"User {user.username} logged out",
        meta={"session_key": session_key},
    )
    UserActivity.objects.create(
        user=user,
        actor=user,
        event_type="logout",
        message="User logged out.",
        meta={"session_key": session_key},
    )
