from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("employee/", views.employee_week, name="employee_week"),
    path("supervisor/", views.supervisor_verify, name="supervisor_verify"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("history/", views.history, name="history"),
    path("history/week/<str:week_start>/", views.history_week, name="history_week"),
    path(
        "history/export/<str:week_start>/<str:fmt>/",
        views.history_export,
        name="history_export",
    ),
]
