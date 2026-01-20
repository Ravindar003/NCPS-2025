from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session

from .models import Participant, AbstractSubmission, ThemeAdmin


class SafeUserAdmin(UserAdmin):
    """
    DEV / TEST ONLY
    Fully removes a test user and ALL foreign-key + M2M references.
    """

    def _cleanup_user(self, user):

        # 1️⃣ Clear M2M relations (CRITICAL)
        user.groups.clear()
        user.user_permissions.clear()

        # 2️⃣ Admin logs
        LogEntry.objects.filter(user=user).delete()

        # 3️⃣ Sessions (dev-safe)
        Session.objects.all().delete()

        # 4️⃣ Abstracts authored
        AbstractSubmission.objects.filter(user=user).delete()

        # 5️⃣ Abstracts approved by user
        AbstractSubmission.objects.filter(
            approved_by=user
        ).update(approved_by=None)

        # 6️⃣ Participant
        Participant.objects.filter(user=user).delete()

        # 7️⃣ Theme admin role
        ThemeAdmin.objects.filter(user=user).delete()

        # 8️⃣ Finally delete user
        user.delete()

    def delete_model(self, request, obj):
        self._cleanup_user(obj)

    def delete_queryset(self, request, queryset):
        for user in queryset:
            self._cleanup_user(user)


admin.site.unregister(User)
admin.site.register(User, SafeUserAdmin)
