from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
import re
import urllib.request
import urllib.parse
import json
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.db.models import Count, Q, F
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .models import PasswordResetOTP
from .utils import get_client_ip
from .admin_views import _get_theme_filtered_abstracts
from .forms import AbstractSubmissionForm
from django.core.cache import cache
from .services.news_fetcher import fetch_official_ncpor_news
from .models import (
    Participant,
    AbstractSubmission,
    ScientificTheme,
    AdminActionLog,
)

# -------------------------------------------------------------------
# HOME
# -------------------------------------------------------------------
def home(request):
    return render(request, "conference/home.html", {
        "is_home": True
    })


# -------------------------------------------------------------------
# PUBLIC INFO PAGES
# -------------------------------------------------------------------
def faq(request):
    return render(request, "conference/faq.html")


def brochure(request):
    return render(request, "conference/brochure.html")


def terms(request):
    return render(request, "conference/terms.html")


def abstract_guidelines(request):
    return render(request, "conference/abstract_guidelines.html")


def abstracts(request):
    return render(request, "conference/abstracts.html")


def themes(request):
    theme_catalog = [
        {
            "code": "crustal_evolution",
            "name": "Crustal Evolution and Reconstruction",
            "image": "images/themes/crustal_evolution.jpg",
            "description": "Sessions focused on tectonics, geodynamics, and the geological evolution of polar and adjacent regions.",
            "topics": [
                "Geochronology and crustal growth",
                "Tectonics and structural geology",
                "Magmatism, metamorphism and basin evolution",
            ],
        },
        {
            "code": "space_weather",
            "name": "Space Weather and Meteorology",
            "image": "images/themes/space_weather.jpg",
            "description": "Explores upper-atmosphere processes, ionospheric variability, and meteorology relevant to polar environments.",
            "topics": [
                "Ionosphere-thermosphere coupling",
                "Geomagnetic storms and impacts",
                "Polar meteorology and boundary-layer processes",
            ],
        },
        {
            "code": "southern_ocean",
            "name": "Southern Ocean in a Changing Climate",
            "image": "images/themes/southern_ocean.jpg",
            "description": "Covers ocean circulation, biogeochemistry, and Southern Ocean processes influencing global climate.",
            "topics": [
                "Ocean circulation and heat transport",
                "Air–sea interaction and sea-ice feedbacks",
                "Carbon cycle and biogeochemistry",
            ],
        },
        {
            "code": "climate_change",
            "name": "Climate Change and Variability",
            "image": "images/themes/climate_change.jpg",
            "description": "Focuses on observations, attribution, and modeling of climate variability and long-term change across regions.",
            "topics": [
                "Observations and reanalysis",
                "Climate extremes and risk",
                "Regional and global modeling",
            ],
        },
        {
            "code": "cryosphere",
            "name": "Cryospheric Processes and Dynamics",
            "image": "images/themes/cryosphere.jpg",
            "description": "Addresses snow, glaciers, ice sheets, and cryosphere–climate interactions including mass balance and dynamics.",
            "topics": [
                "Glacier and ice-sheet mass balance",
                "Snow processes and hydrology",
                "Remote sensing of cryosphere",
            ],
        },
        {
            "code": "sea_ice",
            "name": "Sea Ice Variability and Modelling",
            "image": "images/themes/sea_ice.jpg",
            "description": "Discusses sea-ice observations, prediction, and modeling to understand variability and coupled system impacts.",
            "topics": [
                "Sea-ice thermodynamics and dynamics",
                "Forecasting and predictability",
                "Coupled ocean–ice–atmosphere modeling",
            ],
        },
        {
            "code": "polar_ecology",
            "name": "Polar Environment and Ecology",
            "image": "images/themes/polar_ecology.jpg",
            "description": "Covers ecosystems, biodiversity, and environmental change in polar and high-altitude regions.",
            "topics": [
                "Ecosystem response to warming",
                "Biodiversity and conservation",
                "Biogeochemical and ecological linkages",
            ],
        },
        {
            "code": "polar_operations",
            "name": "Polar Operations, Governance and Outreach",
            "image": "images/themes/polar_operations.jpg",
            "description": "Focuses on logistics, policy, governance, and communication supporting sustained polar research.",
            "topics": [
                "Field logistics and safety",
                "Governance frameworks and compliance",
                "Outreach, education and capacity building",
            ],
        },
    ]

    # If themes exist in DB (admin-controlled), prefer their names.
    db_themes = {t.code: t.name for t in ScientificTheme.objects.all()}
    for t in theme_catalog:
        if t["code"] in db_themes:
            t["name"] = db_themes[t["code"]]

    return render(request, "conference/themes.html", {"themes": theme_catalog})


def theme_detail(request, code):
    theme_catalog = {t["code"]: t for t in [
        {
            "code": "crustal_evolution",
            "name": "Crustal Evolution and Reconstruction",
            "image": "images/themes/crustal_evolution.jpg",
            "description": "Sessions focused on tectonics, geodynamics, and the geological evolution of polar and adjacent regions.",
            "topics": [
                "Geochronology and crustal growth",
                "Tectonics and structural geology",
                "Magmatism, metamorphism and basin evolution",
            ],
        },
        {
            "code": "space_weather",
            "name": "Space Weather and Meteorology",
            "image": "images/themes/space_weather.jpg",
            "description": "Explores upper-atmosphere processes, ionospheric variability, and meteorology relevant to polar environments.",
            "topics": [
                "Ionosphere-thermosphere coupling",
                "Geomagnetic storms and impacts",
                "Polar meteorology and boundary-layer processes",
            ],
        },
        {
            "code": "southern_ocean",
            "name": "Southern Ocean in a Changing Climate",
            "image": "images/themes/southern_ocean.jpg",
            "description": "Covers ocean circulation, biogeochemistry, and Southern Ocean processes influencing global climate.",
            "topics": [
                "Ocean circulation and heat transport",
                "Air–sea interaction and sea-ice feedbacks",
                "Carbon cycle and biogeochemistry",
            ],
        },
        {
            "code": "climate_change",
            "name": "Climate Change and Variability",
            "image": "images/themes/climate_change.jpg",
            "description": "Focuses on observations, attribution, and modeling of climate variability and long-term change across regions.",
            "topics": [
                "Observations and reanalysis",
                "Climate extremes and risk",
                "Regional and global modeling",
            ],
        },
        {
            "code": "cryosphere",
            "name": "Cryospheric Processes and Dynamics",
            "image": "images/themes/cryosphere.jpg",
            "description": "Addresses snow, glaciers, ice sheets, and cryosphere–climate interactions including mass balance and dynamics.",
            "topics": [
                "Glacier and ice-sheet mass balance",
                "Snow processes and hydrology",
                "Remote sensing of cryosphere",
            ],
        },
        {
            "code": "sea_ice",
            "name": "Sea Ice Variability and Modelling",
            "image": "images/themes/sea_ice.jpg",
            "description": "Discusses sea-ice observations, prediction, and modeling to understand variability and coupled system impacts.",
            "topics": [
                "Sea-ice thermodynamics and dynamics",
                "Forecasting and predictability",
                "Coupled ocean–ice–atmosphere modeling",
            ],
        },
        {
            "code": "polar_ecology",
            "name": "Polar Environment and Ecology",
            "image": "images/themes/polar_ecology.jpg",
            "description": "Covers ecosystems, biodiversity, and environmental change in polar and high-altitude regions.",
            "topics": [
                "Ecosystem response to warming",
                "Biodiversity and conservation",
                "Biogeochemical and ecological linkages",
            ],
        },
        {
            "code": "polar_operations",
            "name": "Polar Operations, Governance and Outreach",
            "image": "images/themes/polar_operations.jpg",
            "description": "Focuses on logistics, policy, governance, and communication supporting sustained polar research.",
            "topics": [
                "Field logistics and safety",
                "Governance frameworks and compliance",
                "Outreach, education and capacity building",
            ],
        },
    ]}

    theme = theme_catalog.get(code)
    if not theme:
        return render(request, "conference/theme_detail.html", {"theme": None}, status=404)

    try:
        db_theme = ScientificTheme.objects.get(code=code)
        theme = {**theme, "name": db_theme.name}
    except ScientificTheme.DoesNotExist:
        pass

    return render(request, "conference/theme_detail.html", {"theme": theme})


# -------------------------------------------------------------------
# AUTH
# -------------------------------------------------------------------
def user_login(request):
    if request.method == "POST":
        # accept email from the form; fallback to username if provided
        email = request.POST.get("email")
        password = request.POST.get("password")
        username = None

        if email:
            users_qs = User.objects.filter(email__iexact=email)
            if users_qs.count() == 1:
                username = users_qs.first().username
            elif users_qs.count() > 1:
                # multiple users share this email; try authenticating each by username
                username = None
                for u in users_qs:
                    candidate = authenticate(request, username=u.username, password=password)
                    if candidate is not None:
                        username = u.username
                        break
                # if none authenticated, fall back to username field (to show standard invalid message)
                if not username:
                    username = request.POST.get("username")
            else:
                # if no user with this email, allow fallback to username field
                username = request.POST.get("username")
        else:
            username = request.POST.get("username")
        next_url = request.POST.get("next") or request.GET.get("next")

        user = None
        if username:
            user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            AdminActionLog.objects.create(
                user=user,
                action="LOGIN",
                ip_address=get_client_ip(request),
                description="User logged in"
            )

            if user.is_superuser:
                return redirect("conference:ncps_admin:dashboard")

            if hasattr(user, "theme_admin") and user.theme_admin.is_active:
                return redirect("conference:ncps_admin:theme_dashboard")

            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("conference:dashboard")

        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "conference/login.html")


@login_required
def user_logout(request):
    AdminActionLog.objects.create(
        user=request.user,
        action="LOGOUT",
        ip_address=get_client_ip(request),
        description="User logged out"
    )
    logout(request)
    return redirect("conference:home")


# -------------------------------------------------------------------
# REGISTRATION
# -------------------------------------------------------------------
def register(request):
    if request.method == "POST":
        # registration now uses email only; username will be generated
        raw_username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        email_confirm = request.POST.get("email_confirm", "").strip()
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        title = request.POST.get("title", "").strip()
        organization = request.POST.get("organization", "").strip()
        designation = request.POST.get("designation", "").strip()
        phone = request.POST.get("phone", "").strip()
        scientific_theme = request.POST.get("scientific_theme", "").strip()

        # ---------------- VALIDATIONS ----------------
        # required fields: email, email_confirm, password1, scientific_theme, first_name, phone
        if not all([email, email_confirm, password1, scientific_theme, first_name, phone]):
            messages.error(request, "All required fields must be filled.")
            return redirect("conference:register")

        if email != email_confirm:
            messages.error(request, "Email and confirmation do not match.")
            return redirect("conference:register")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("conference:register")
        # First name validation: must contain alphabetic characters (cannot be numbers only)
        if not re.search(r"[A-Za-z]", first_name):
            messages.error(request, "First name must include alphabetic characters and cannot be numbers only.")
            return redirect("conference:register")
        # ---------------- STRONG PASSWORD VALIDATION ----------------
        # Enforce: min 10 chars, upper, lower, digit, special char
        pwd = password1 or ""
        pwd_errors = []
        if len(pwd) < 10:
            pwd_errors.append("Password must be at least 10 characters long.")
        if not re.search(r"[A-Z]", pwd):
            pwd_errors.append("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", pwd):
            pwd_errors.append("Password must include at least one lowercase letter.")
        if not re.search(r"\d", pwd):
            pwd_errors.append("Password must include at least one digit.")
        if not re.search(r"[!@#$%^&*()_+\-=[\]{};':\"\\|,.<>/?]", pwd):
            pwd_errors.append("Password must include at least one special character (e.g. !@#$%).")

        # Also run Django's configured password validators if any
        try:
            validate_password(pwd)
        except ValidationError as e:
            for msg in e.messages:
                pwd_errors.append(msg)

        if pwd_errors:
            for e_msg in pwd_errors:
                messages.error(request, e_msg)
            return redirect("conference:register")
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("conference:register")
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address.")
            return redirect("conference:register")

        # Phone is expected as the 10-digit national number (excluding country code).
        # A fixed country code (+91) is submitted via a hidden field.
        phone_part = request.POST.get("phone", "").strip()
        country_code = request.POST.get("country_code", "+91").strip() or "+91"

        # Validate numeric and exact length
        if not phone_part.isdigit():
            messages.error(request, "Phone number must contain digits only.")
            return redirect("conference:register")

        if len(phone_part) != 10:
            messages.error(request, "Phone number must be exactly 10 digits (excluding country code).")
            return redirect("conference:register")

        phone = f"{country_code}{phone_part}"
        # ---------------- Google reCAPTCHA CHECK ----------------
        recaptcha_response = request.POST.get('g-recaptcha-response', '')
        secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
        if not secret:
            messages.error(request, "reCAPTCHA not configured on the server. Please contact the administrator.")
            return redirect('conference:register')

        if not recaptcha_response:
            messages.error(request, "Please complete the reCAPTCHA.")
            return redirect('conference:register')

        verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        data = urllib.parse.urlencode({
            'secret': secret,
            'response': recaptcha_response,
            'remoteip': get_client_ip(request),
        }).encode()
        try:
            req = urllib.request.Request(verify_url, data=data)
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
        except Exception:
            messages.error(request, "reCAPTCHA verification failed (network). Please try again.")
            return redirect('conference:register')

        if not result.get('success'):
            messages.error(request, "reCAPTCHA verification failed. Please try again.")
            return redirect('conference:register')
        # ---------------- CREATE USER ----------------
        # generate a username from the email local-part and ensure uniqueness
        if raw_username:
            base_username = raw_username
        else:
            base_username = re.sub(r"[^a-zA-Z0-9_]", "_", email.split("@")[0])

        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )

        # ---------------- CREATE PARTICIPANT ----------------
        Participant.objects.get_or_create(
            user=user,
            defaults={
                "title": title,
                "organization": organization,
                "designation": designation,
                "phone": phone,
                "scientific_theme": scientific_theme,
            },
        )

        messages.success(request, "Registration successful. Please log in.")
        return redirect("conference:login")

    # Build theme choices identical to the home/themes `theme_catalog` (same codes, order, and names)
    theme_catalog = [
        {
            "code": "crustal_evolution",
            "name": "Crustal Evolution and Reconstruction",
        },
        {
            "code": "space_weather",
            "name": "Space Weather and Meteorology",
        },
        {
            "code": "southern_ocean",
            "name": "Southern Ocean in a Changing Climate",
        },
        {
            "code": "climate_change",
            "name": "Climate Change and Variability",
        },
        {
            "code": "cryosphere",
            "name": "Cryospheric Processes and Dynamics",
        },
        {
            "code": "sea_ice",
            "name": "Sea Ice Variability and Modelling",
        },
        {
            "code": "polar_ecology",
            "name": "Polar Environment and Ecology",
        },
        {
            "code": "polar_operations",
            "name": "Polar Operations, Governance and Outreach",
        },
    ]

    try:
        db_themes = {t.code: t.name for t in ScientificTheme.objects.all()}
    except Exception:
        db_themes = {}

    theme_choices = []
    for t in theme_catalog:
        code = t["code"]
        name = db_themes.get(code, t["name"])
        theme_choices.append((code, name))

    recaptcha_site_key = getattr(settings, 'RECAPTCHA_SITE_KEY', '')
    return render(request, "conference/register.html", {"theme_choices": theme_choices, "recaptcha_site_key": recaptcha_site_key})


# -------------------------------------------------------------------
# USER DASHBOARD
# -------------------------------------------------------------------
@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect("conference:ncps_admin:dashboard")


    abstracts = AbstractSubmission.objects.filter(
        user=request.user
    ).order_by("-submitted_at")

    notifications = (
        request.user.notifications.all()[:5]
        if hasattr(request.user, "notifications")
        else []
    )

    notifications_count = (
        request.user.notifications.filter(is_read=False).count()
        if hasattr(request.user, "notifications")
        else 0
    )


    context = {
        "submissions_count": abstracts.count(),
        "abstracts": abstracts,
        "abstract_deadline": "15 January 2025",
        "notifications": notifications,
        "notifications_count": request.user.notifications.filter(is_read=False).count(),
        # participant_theme_name: prefer admin-controlled ScientificTheme.name when available
        "participant_theme_name": None,
    }

    # Use the exact label selected during registration (participant choice)
    try:
        participant = request.user.participant
        # Participant.scientific_theme may contain legacy short codes (e.g. 'ocean').
        # Prefer canonical choice labels; map common legacy keys to current codes.
        code = (participant.scientific_theme or "").strip()
        valid_codes = [c for c, _ in Participant.SCIENTIFIC_THEMES]
        alias_map = {
            "ocean": "oceanography",
            "oceans": "oceanography",
            "polar_ocean": "oceanography",
        }

        if code not in valid_codes and code.lower() in alias_map:
            mapped = alias_map[code.lower()]
            # use choice label if available
            label = dict(Participant.SCIENTIFIC_THEMES).get(mapped)
            context["participant_theme_name"] = label or mapped
        else:
            context["participant_theme_name"] = participant.get_scientific_theme_display()
    except Exception:
        context["participant_theme_name"] = None

    return render(request, "conference/dashboard.html", context)


@login_required
def notifications_list(request):
    notifications = request.user.notifications.all()
    return render(
        request,
        "conference/notifications.html",
        {
            "notifications": notifications,
            "notifications_count": notifications.filter(is_read=False).count(),
        },
    )



# -------------------------------------------------------------------
# PROFILE
# -------------------------------------------------------------------
@login_required
def profile_view(request):
    return render(
        request,
        "conference/profile.html",
        {
            "user_obj": request.user,
            "participant": getattr(request.user, "participant", None),
        },
    )


@login_required
def profile_edit(request):
    user = request.user
    participant = getattr(user, "participant", None)

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.save()

        if participant:
            # Title (Mr/Ms/Dr/etc)
            participant.title = request.POST.get("title", participant.title)
            participant.organization = request.POST.get("organization", "").strip()
            participant.designation = request.POST.get("designation", "").strip()
            participant.phone = request.POST.get("phone", "").strip()
            participant.scientific_theme = request.POST.get(
                "scientific_theme", participant.scientific_theme
            )
            participant.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    return render(request, "conference/profile_edit.html")


# -------------------------------------------------------------------
# ABSTRACT SUBMISSION
# -------------------------------------------------------------------
@login_required
def abstract_submission(request):
    if request.method == "POST":
        form = AbstractSubmissionForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Please correct the errors below.")
            return render(
                request,
                "conference/abstract_submission.html",
                {"form": form},
            )

        abstract = form.save(commit=False)
        abstract.user = request.user

        # Assign the user's registered scientific theme automatically
        try:
            participant = request.user.participant
            theme_code = participant.scientific_theme
            theme_obj = ScientificTheme.objects.get(code=theme_code)
            abstract.theme = theme_obj
        except Participant.DoesNotExist:
            messages.error(request, "Please complete your profile with a scientific theme before submitting an abstract.")
            return render(request, "conference/abstract_submission.html", {"form": form, "user_theme": None})
        except ScientificTheme.DoesNotExist:
            messages.error(request, "Your selected scientific theme is not available. Contact admin.")
            return render(request, "conference/abstract_submission.html", {"form": form, "user_theme": None})
        # Enforce PDF-only: ensure a PDF file was uploaded
        pdf_file = abstract.pdf_file
        if not pdf_file:
            messages.error(request, "Please upload a PDF file for your abstract.")
            return render(request, "conference/abstract_submission.html", {"form": form})

        # Basic server-side validation for file type/size
        uploaded = request.FILES.get('pdf_file')
        if uploaded:
            if not uploaded.name.lower().endswith('.pdf'):
                messages.error(request, "Uploaded file must be a PDF.")
                return render(request, "conference/abstract_submission.html", {"form": form})
            if uploaded.size > 20 * 1024 * 1024:
                messages.error(request, "PDF must be 20 MB or smaller.")
                return render(request, "conference/abstract_submission.html", {"form": form})

        # ---------------------------------------
        # 3️⃣ Save safely
        # ---------------------------------------
        abstract.save()
        messages.success(request, "Abstract submitted successfully.")
        return redirect("conference:dashboard")


    form = AbstractSubmissionForm()
    # provide user's selected theme name for display
    user_theme = None
    try:
        user_theme = ScientificTheme.objects.get(code=request.user.participant.scientific_theme).name
    except Exception:
        user_theme = None

    return render(
        request,
        "conference/abstract_submission.html",
        {"form": form, "user_theme": user_theme},
    )

# -------------------------------------------------------------------
# UPLOAD REVISED ABSTRACT
# -------------------------------------------------------------------
@login_required
def upload_revised_abstract(request, pk):
    abstract = get_object_or_404(
        AbstractSubmission,
        pk=pk,
        user=request.user
    )

    if abstract.status != "REVISION":
        messages.error(request, "Revision is not required for this abstract.")
        return redirect("conference:dashboard")

    # ⏳ Deadline enforcement
    if abstract.revision_due_date and timezone.now().date() > abstract.revision_due_date:
        messages.error(request, "Revision deadline has passed.")
        return redirect("conference:dashboard")

    if request.method == "POST":
        revised_file = request.FILES.get("revised_submission")

        # Require PDF-only revised submission
        if not revised_file:
            messages.error(request, "Please upload a revised PDF file.")
            return redirect(request.path)

        # Basic server-side checks
        if not revised_file.name.lower().endswith('.pdf'):
            messages.error(request, "Revised submission must be a PDF file.")
            return redirect(request.path)
        if revised_file.size > 20 * 1024 * 1024:
            messages.error(request, "Revised PDF must be 20 MB or smaller.")
            return redirect(request.path)

        abstract.revised_submission = revised_file
        abstract.revised_uploaded_at = timezone.now()
        abstract.status = "RESUBMITTED"
        abstract.admin_comments = None
        abstract.revision_due_date = None
        abstract.save()

        messages.success(request, "Revision submitted successfully.")
        return redirect("conference:dashboard")

    return render(
        request,
        "conference/upload_revised_abstract.html",
        {"abstract": abstract}
    )
@staff_member_required
def theme_admin_participant_detail(request, pk):
    user = request.user

    if not hasattr(user, "theme_admin") or not user.theme_admin.is_active:
        return HttpResponseForbidden("Not authorized")

    participant = get_object_or_404(
        Participant.objects.select_related("user"),
        pk=pk
    )

    themes = user.theme_admin.themes.all()

    # ✅ SECURITY CHECK: participant must have abstracts in admin themes
    if not AbstractSubmission.objects.filter(
        user=participant.user,
        theme__in=themes
    ).exists():
        return HttpResponseForbidden("Not authorized for this participant")

    abstracts = AbstractSubmission.objects.filter(
        user=participant.user,
        theme__in=themes
    )

    return render(
        request,
        "admin/theme_registration_detail.html",
        {
            "registration": participant,
            "abstracts": abstracts,
        }
    )

@staff_member_required
def theme_participants(request):
    user = request.user

    if not hasattr(user, "theme_admin") or not user.theme_admin.is_active:
        return HttpResponseForbidden("Not authorized")

    themes = user.theme_admin.themes.all()

    participants = Participant.objects.filter(
        user__abstracts__theme__in=themes
    ).select_related("user").annotate(
        theme_abstract_count=Count(
            "user__abstracts",
            filter=Q(user__abstracts__theme__in=themes),
            distinct=True
        )
    ).distinct()


    return render(
        request,
        "admin/theme_participants.html",
        {"participants": participants}
    )

# -------------------------------------------------------------------
# USER ABSTRACT DETAIL (READ-ONLY)
# -------------------------------------------------------------------
@login_required
def user_abstract_detail(request, pk):
    abstract = get_object_or_404(
        AbstractSubmission,
        pk=pk,
        user=request.user   # 🔐 user can see ONLY their own abstract
    )

    return render(
        request,
        "conference/abstract_detail.html",
        {
            "abstract": abstract
        }
    )


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            messages.error(request, "Email address is required.")
            return redirect("conference:forgot_password")

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Enter a valid email address.")
            return redirect("conference:forgot_password")

        # Try to find user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 🔒 Security: don't reveal account existence
            messages.success(
                request,
                "If an account exists with this email, an OTP has been sent."
            )
            return redirect("conference:forgot_password")

        # User exists → continue OTP flow
        if not user.email:
            messages.error(
                request,
                "No email is associated with this account. Contact support."
            )
            return redirect("conference:forgot_password")

        # Remove previous unused OTPs
        PasswordResetOTP.objects.filter(
            user=user,
            is_used=False
        ).delete()

        otp = PasswordResetOTP.generate_otp()
        PasswordResetOTP.objects.create(user=user, otp=otp)

        # DEV only
        print(f"🔐 PASSWORD RESET OTP for {user.email}: {otp}")

        send_mail(
            subject="Password Reset OTP",
            message=f"Your OTP is {otp}. Valid for 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        # ✅ REQUIRED session values
        request.session["reset_user_id"] = user.id
        request.session["otp_last_sent"] = timezone.now().timestamp()

        messages.success(
            request,
            "If an account exists with this email, an OTP has been sent."
        )
        return redirect("conference:verify_otp")

    # ✅ ALWAYS return response for GET
    return render(
        request,
        "conference/forgot_password/forgot_password.html"
    )

def verify_otp(request):
    user_id = request.session.get("reset_user_id")

    if not user_id:
        return redirect("conference:forgot_password")

    if request.method == "POST":
        otp_input = request.POST.get("otp")

        otp_obj = PasswordResetOTP.objects.filter(
            user_id=user_id,
            otp=otp_input,
            is_used=False
        ).last()

        if not otp_obj:
            messages.error(request, "Invalid OTP")
            return redirect("conference:verify_otp")

        if otp_obj.is_expired():
            messages.error(request, "OTP expired")
            return redirect("conference:forgot_password")

        otp_obj.is_used = True
        otp_obj.save()

        request.session["otp_verified"] = True
        return redirect("conference:reset_password")

    return render(request, "conference/forgot_password/verify_otp.html")


def resend_otp(request):
    user_id = request.session.get("reset_user_id")

    if not user_id:
        messages.error(request, "Session expired. Please try again.")
        return redirect("conference:forgot_password")

    last_sent_ts = request.session.get("otp_last_sent")

    if last_sent_ts:
        last_sent_time = timezone.datetime.fromtimestamp(
            last_sent_ts,
            tz=timezone.get_current_timezone()
        )

        elapsed = timezone.now() - last_sent_time
        if elapsed < timedelta(seconds=30):
            remaining = 30 - int(elapsed.total_seconds())
            messages.warning(
                request,
                f"Please wait {remaining} seconds before requesting a new OTP."
            )
            return redirect("conference:verify_otp")

    user = User.objects.get(id=user_id)

    # Invalidate previous OTPs
    PasswordResetOTP.objects.filter(
        user=user,
        is_used=False
    ).update(is_used=True)

    otp = PasswordResetOTP.generate_otp()
    PasswordResetOTP.objects.create(user=user, otp=otp)

    # DEV: print OTP
    print(f"🔁 RESENT OTP for {user.username}: {otp}")

    send_mail(
        subject="Password Reset OTP (Resent)",
        message=f"Your new OTP is {otp}. Valid for 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    # ✅ Store timestamp, NOT datetime
    request.session["otp_last_sent"] = timezone.now().timestamp()

    messages.success(request, "A new OTP has been sent to your email.")
    return redirect("conference:verify_otp")


def reset_password(request):
    user_id = request.session.get("reset_user_id")
    otp_verified = request.session.get("otp_verified")

    if not user_id or not otp_verified:
        return redirect("conference:forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("conference:reset_password")

        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        AdminActionLog.objects.create(
            user=user,
            action="PASSWORD_RESET",
            ip_address=get_client_ip(request),
            description="User reset password via OTP"
        )

        request.session.flush()

        messages.success(request, "Password reset successful. Login now.")
        return redirect("conference:login")

    return render(request, "conference/forgot_password/reset_password.html")
def past_conferences(request):
    return render(request, "conference/past_conferences.html")
