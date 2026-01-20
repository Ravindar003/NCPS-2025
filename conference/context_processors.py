from .models import ScientificTheme, Participant
from .models import Notification


def theme_choices(request):
    """Provide the canonical theme list to templates.

    Uses admin-defined ScientificTheme names when present, otherwise falls
    back to the Participant.SCIENTIFIC_THEMES labels. Returns `theme_choices`
    as a list of (code, name) tuples in the preferred order.
    """
    theme_catalog = [
        {"code": "crustal_evolution", "name": "Crustal Evolution and Reconstruction"},
        {"code": "space_weather", "name": "Space Weather and Meteorology"},
        {"code": "southern_ocean", "name": "Southern Ocean in a Changing Climate"},
        {"code": "climate_change", "name": "Climate Change and Variability"},
        {"code": "cryosphere", "name": "Cryospheric Processes and Dynamics"},
        {"code": "sea_ice", "name": "Sea Ice Variability and Modelling"},
        {"code": "polar_ecology", "name": "Polar Environment and Ecology"},
        {"code": "polar_operations", "name": "Polar Operations, Governance and Outreach"},
    ]

    try:
        db_themes = {t.code: t.name for t in ScientificTheme.objects.all()}
    except Exception:
        db_themes = {}

    # Participant choices fallback map
    choice_map = dict(Participant.SCIENTIFIC_THEMES)

    theme_choices = []
    for t in theme_catalog:
        code = t["code"]
        name = db_themes.get(code, choice_map.get(code, t["name"]))
        theme_choices.append((code, name))

    return {"theme_choices": theme_choices}


def notification_count(request):
    """Provide unread notification count for logged-in users."""
    try:
        user = request.user
        if user and user.is_authenticated:
            # Superuser sees global unread count
            if getattr(user, "is_superuser", False):
                count = Notification.objects.filter(is_read=False).count()
            else:
                count = Notification.objects.filter(user=user, is_read=False).count()
        else:
            count = 0
    except Exception:
        count = 0

    return {"unread_notifications_count": count}
