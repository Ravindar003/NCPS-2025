# conference/urls.py
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = "conference"

urlpatterns = [
    # Public
    path("", views.home, name="home"),
    path("themes/", views.themes, name="themes"),
    path("themes/<slug:code>/", views.theme_detail, name="theme_detail"),
    path("brochure/", views.brochure, name="brochure"),
    path("faq/", views.faq, name="faq"),
    path("terms/", views.terms, name="terms"),
    path(
        "abstract-guidelines/",
        views.abstract_guidelines,
        name="abstract_guidelines",
    ),
    path("abstracts/", views.abstracts, name="abstracts"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("register/", views.register, name="register"),

    # User
    path("dashboard/", views.dashboard, name="dashboard"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("abstract-submission/", views.abstract_submission, name="abstract_submission"),
    path("submit-abstract/", views.abstract_submission, name="submit_abstract"),

    path(
        "abstract/<int:pk>/upload-revision/",
        views.upload_revised_abstract,
        name="upload_revised_abstract",
    ),
    path(
        "abstract/<int:pk>/",
        views.user_abstract_detail,
        name="user_abstract_detail",
    ),

    # Profile
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),

    # Password / OTP
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("reset-password/", views.reset_password, name="reset_password"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),

    # Admin
    path(
        "admin-dashboard/",
        include(("conference.admin_urls", "ncps_admin"), namespace="ncps_admin"),
    ),
    path(
    "past-conferences/",
    views.past_conferences,
    name="past_conferences"
)
]

# ✅ MEDIA FILES (DEV ONLY)
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
