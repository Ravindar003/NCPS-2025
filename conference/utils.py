# conference/utils.py

from .models import AdminActionLog


def get_client_ip(request):
    """
    Safely return the client IP address
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_admin_action(request, action, description="", obj=None):
    """
    Centralized admin/user action logger
    """
    AdminActionLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        object_type=obj.__class__.__name__ if obj else None,
        object_id=obj.id if obj else None,
        description=description,
        ip_address=get_client_ip(request),
    )
