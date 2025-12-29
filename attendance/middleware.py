from datetime import timedelta

from django.utils import timezone

from .models import UserDailyLogin, UserSession
from .utils import get_client_ip


class ActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            return response

        now = timezone.now()
        last_seen_ts = request.session.get("last_seen_ts")
        if last_seen_ts:
            last_seen = timezone.datetime.fromtimestamp(last_seen_ts, tz=timezone.utc)
            if now - last_seen < timedelta(minutes=1):
                return response

        request.session["last_seen_ts"] = int(now.timestamp())
        today = timezone.localdate()
        ip_address = get_client_ip(request)

        UserDailyLogin.objects.update_or_create(
            user=request.user,
            date=today,
            defaults={
                "last_seen_at": now,
                "last_ip": ip_address,
                "online": True,
            },
        )

        session_key = request.session.session_key
        if session_key:
            UserSession.objects.filter(
                user=request.user, session_key=session_key, is_active=True
            ).update(last_seen_at=now, ip_address=ip_address)

        return response
