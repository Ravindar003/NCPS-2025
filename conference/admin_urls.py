# conference/admin_urls.py
from django.urls import path
from . import admin_views, views

app_name = "ncps_admin"

urlpatterns = [
    # Dashboard
    path("", admin_views.admin_dashboard, name="dashboard"),

    # Logs
    path("logs/", admin_views.admin_logs, name="admin_logs"),
    path("logs/export/", admin_views.export_admin_logs, name="export_admin_logs"),

    # Abstracts
    path("abstracts/", admin_views.admin_abstracts, name="abstracts"),
    path("abstracts/<int:pk>/", admin_views.admin_abstract_detail, name="abstract_detail"),
    path(
        "abstracts/<int:pk>/update-status/",
        admin_views.admin_update_abstract_status,
        name="update_abstract_status",
    ),
    path(
        "abstracts/<int:pk>/assign-reviewer/",
        admin_views.assign_abstract_reviewer,
        name="assign_abstract_reviewer",
    ),
    path(
        "abstracts/<int:pk>/submit-review/",
        admin_views.submit_review_comment,
        name="submit_review_comment",
    ),
    path("abstracts/export/", admin_views.admin_export_abstracts, name="export_abstracts"),

    # Registrations
    path("registrations/", admin_views.admin_registrations, name="registrations"),
    path(
        "registrations/<int:pk>/",
        admin_views.admin_registration_detail,
        name="registration_detail",
    ),
    path(
        "registrations/export/",
        admin_views.admin_export_registrations,
        name="export_registrations",
    ),

    # Analytics
    path("analytics/", admin_views.admin_analytics, name="analytics"),

    # Theme Admins
    path("theme-admins/", admin_views.theme_admin_list, name="theme_admin_list"),
    path("theme-admins/add/", admin_views.theme_admin_create, name="theme_admin_create"),
    path("theme-admins/<int:pk>/edit/", admin_views.theme_admin_edit, name="theme_admin_edit"),
    path("theme-admins/<int:pk>/toggle/", admin_views.theme_admin_toggle, name="theme_admin_toggle"),
    path("theme-admins/<int:pk>/delete/", admin_views.theme_admin_delete, name="theme_admin_delete"),

    # Theme dashboard
    path("theme/", admin_views.theme_admin_dashboard, name="theme_dashboard"),
    path("notifications/", admin_views.theme_admin_notifications, name="notifications"),

    # Theme admin participant detail
    path(
        "participants/<int:pk>/",
        views.theme_admin_participant_detail,
        name="theme_admin_participant_detail",
    ),

    # Logout
    path("logout/", views.user_logout, name="logout"),
]
