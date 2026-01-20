# project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ conference app (ONLY ONCE)
    path(
        "",
        include(("conference.urls", "conference"), namespace="conference"),
    ),

    path("chatbot/", include("chatbot.urls")),
]
