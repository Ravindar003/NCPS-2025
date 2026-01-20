from datetime import datetime
import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, F
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from .utils import log_admin_action
from datetime import timedelta
from .models import (
    AbstractSubmission,
    Participant,
    Notification,
    ThemeAdmin,
    AbstractReview,
    AdminActionLog,
    ScientificTheme,  
)
from django.core.mail import send_mail
from django.conf import settings
import json
from .context_processors import theme_choices as get_theme_choices




# ==================================================
# HELPER: THEME ADMIN CHECK
# ==================================================
def _get_theme_filtered_abstracts(user):
    """
    Returns queryset filtered by theme for theme admins,
    or all for superuser.
    """
    if user.is_superuser:
        return AbstractSubmission.objects.select_related("user", "theme")

    if hasattr(user, "theme_admin") and user.theme_admin.is_active:
        themes = user.theme_admin.themes.all()
        return AbstractSubmission.objects.select_related(
            "user", "theme"
        ).filter(theme__in=themes)

    return None



@staff_member_required
def admin_logs(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    logs_qs = AdminActionLog.objects.select_related("user").order_by("created_at")
    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params._mutable = True
    query_params.setlist("page", [])


    # -------- FILTERS --------
    action = request.GET.get("action")
    user_id = request.GET.get("user")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if action:
        logs_qs = logs_qs.filter(action=action)

    if user_id and user_id.isdigit():
        logs_qs = logs_qs.filter(user__id=int(user_id))

    if start_date:
        try:
            logs_qs = logs_qs.filter(created_at__date__gte=start_date)
        except ValueError:
            pass

    if end_date:
        try:
            logs_qs = logs_qs.filter(created_at__date__lte=end_date)
        except ValueError:
            pass

    # -------- PAGINATION --------
    paginator = Paginator(logs_qs, 20)  # 20 logs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    query_string = query_params.urlencode()

    context = {
        "logs": page_obj,
        "actions": AdminActionLog.ACTION_CHOICES,
        "users": User.objects.filter(is_staff=True),
        "page_obj": page_obj,
        "query_string": query_string,
    }



    return render(request, "admin/admin_logs.html", context)


# ==================================================
# DASHBOARD
# ==================================================
@staff_member_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect("conference:ncps_admin:theme_dashboard")


    total_abstracts = AbstractSubmission.objects.count()
    total_registrations = Participant.objects.count()

    status_stats = (
        AbstractSubmission.objects
        .values("status")
        .annotate(count=Count("status"))
    )
    status_map = {s["status"]: s["count"] for s in status_stats}

    recent_abstracts = (
        AbstractSubmission.objects
        .select_related("user")
        .order_by("-submitted_at")[:10]
    )

    recent_registrations = (
        Participant.objects
        .select_related("user")
        .order_by("-created_at")[:10]
    )

    context = {
        "total_abstracts": total_abstracts,
        "total_registrations": total_registrations,
        "recent_abstracts": recent_abstracts,
        "recent_registrations": recent_registrations,
        "pending_count": status_map.get("PENDING", 0),
        "revision_count": status_map.get("REVISION", 0),
        "approved_count": status_map.get("APPROVED", 0),
        "rejected_count": status_map.get("REJECTED", 0),
    }

    # No notifications are passed here; notifications live on the dedicated page

    return render(request, "admin/dashboard.html", context)


# ==================================================
# ABSTRACT LIST
# ==================================================
@staff_member_required
def admin_abstracts(request):
    user = request.user
    abstracts = _get_theme_filtered_abstracts(user)

    if abstracts is None:
        return HttpResponseForbidden("You are not authorized to view abstracts.")

    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("search", "")
    theme_filter = request.GET.get("theme", "")

    if status_filter:
        abstracts = abstracts.filter(status=status_filter)

    if search_query:
        abstracts = abstracts.filter(
            Q(title__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Theme filter (by ScientificTheme.code)
    if theme_filter:
        abstracts = abstracts.filter(theme__code=theme_filter)

    # Use canonical 8-theme list (falls back to DB names where present)
    theme_choices = get_theme_choices(request).get('theme_choices', [])
    # convert to list of dicts for template compatibility (t.code / t.name)
    themes = [{"code": code, "name": name} for code, name in theme_choices]

    context = {
        "abstracts": abstracts.order_by("-submitted_at"),
        "status_choices": [
            c for c in AbstractSubmission.STATUS_CHOICES
            if c[0] != "RESUBMITTED"
        ],

        "current_status": status_filter,
        "current_theme": theme_filter,
        "themes": themes,
        "search_query": search_query,
        "is_superuser": user.is_superuser,
    }

    return render(request, "admin/abstracts_list.html", context)


# ==================================================
# ABSTRACT DETAIL
# ==================================================
@staff_member_required
def admin_abstract_detail(request, pk):
    user = request.user

    abstract = get_object_or_404(
        AbstractSubmission.objects.select_related("user", "theme"),
        pk=pk
    )

    participant = getattr(abstract.user, "participant", None)

    # ==================================================
    # REVIEWER CHECK (STRICT & SAFE)
    # ==================================================
    is_reviewer = False
    review_obj = None

    if hasattr(user, "theme_admin") and user.theme_admin.is_active:
        review_obj = AbstractReview.objects.filter(
            abstract=abstract,
            reviewer=user.theme_admin
        ).first()

        # If a review record exists for this theme admin, treat them as reviewer
        if review_obj:
            is_reviewer = True

    # ==================================================
    # CAN MANAGE (SUPERUSER / THEME OWNER)
    # ==================================================
    can_manage = (
        user.is_superuser or
        (
            hasattr(user, "theme_admin")
            and user.theme_admin.is_active
            and abstract.theme in user.theme_admin.themes.all()
        )
    )

    # ==================================================
    # AUTHORIZATION
    # ==================================================
    if not user.is_superuser and not (can_manage or is_reviewer):
        return HttpResponseForbidden("Not authorized.")

    # ==================================================
    # DATA FOR TEMPLATE
    # ==================================================
    available_reviewers = ThemeAdmin.objects.filter(
        is_active=True
    ).exclude(user=user)

    existing_reviews = AbstractReview.objects.select_related(
        "reviewer", "reviewer__user"
    ).filter(
        abstract=abstract,
        is_submitted=True
    )

    context = {
        "abstract": abstract,
        "participant": participant,
                    "status_choices": [
                c for c in AbstractSubmission.STATUS_CHOICES
                if c[0] != "RESUBMITTED"
            ],


        # flags
        "can_manage": can_manage,
        "is_reviewer": is_reviewer,
        "review_obj": review_obj,
        "is_superuser": user.is_superuser,

        # data
        "available_reviewers": available_reviewers,
        "existing_reviews": existing_reviews,
    }

    return render(
        request,
        "admin/abstract_detail.html",
        context
    )

# ==================================================
# UPDATE ABSTRACT STATUS
# ==================================================
@staff_member_required
def admin_update_abstract_status(request, pk):
    user = request.user
    abstract = get_object_or_404(AbstractSubmission, pk=pk)

    if not user.is_superuser:
        if not hasattr(user, "theme_admin") or not user.theme_admin.is_active:
            return HttpResponseForbidden("Not authorized.")
        if abstract.theme not in user.theme_admin.themes.all():
            return HttpResponseForbidden("Not authorized for this theme.")

    if request.method != "POST":
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    status = request.POST.get("status")
    admin_comments = request.POST.get("admin_comments", "").strip()
    revision_due_date_raw = request.POST.get("revision_due_date")

    ADMIN_ALLOWED_STATUSES = {
        "PENDING",
        "REVISION",
        "APPROVED",
        "REJECTED"
    }

    if status not in ADMIN_ALLOWED_STATUSES:
        messages.error(request, "Invalid status selected.")
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)



    revision_due_date = None
    if revision_due_date_raw:
        try:
            revision_due_date = datetime.strptime(
                revision_due_date_raw, "%Y-%m-%d"
            ).date()
        except ValueError:
            messages.error(request, "Invalid revision due date.")
            return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    if status == "REVISION" and not revision_due_date:
        messages.error(request, "Revision requires a due date.")
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    if status == "REJECTED" and not admin_comments:
        messages.error(request, "Rejection requires a reason.")
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    # ---------- UPDATE ABSTRACT ----------
    abstract.status = status
    abstract.admin_comments = admin_comments or None

    if status == "REVISION":
        abstract.revision_due_date = revision_due_date
        abstract.approved_by = None
        abstract.approved_at = None
        abstract.revised_submission = None
        abstract.revised_uploaded_at = None

    elif status == "APPROVED":
        abstract.approved_by = user
        abstract.approved_at = timezone.now()
        abstract.revision_due_date = None

    elif status == "REJECTED":
        abstract.revision_due_date = None
        abstract.approved_by = None
        abstract.approved_at = None


    abstract.save()

    messages.success(
        request,
        f"Abstract marked as {abstract.get_status_display()}."
    )

    # ---------- 🔔 CREATE NOTIFICATION ----------
    comment = (abstract.admin_comments or "").strip()

    Notification.objects.create(
        user=abstract.user,
        abstract=abstract,
        title=f"Abstract {abstract.get_status_display()}",
        message=(
            f"Your abstract '{abstract.title}' was marked as "
            f"{abstract.get_status_display()}."
            + (
                f"\n\nReviewer comment:\n{comment}"
                if comment else ""
            )
        )
    )
    ACTION_MAP = {
        "APPROVED": "APPROVED",
        "REJECTED": "REJECTED",
        "REVISION": "UPDATE"
    }


    log_admin_action(
        request,
        action=ACTION_MAP.get(status, "UPDATE"),
        obj=abstract,
        description=f"Status changed to {status}"
    )


    return redirect("conference:ncps_admin:abstract_detail", pk=pk)


# ==================================================
# EXPORT ABSTRACTS (THEME SAFE)
# ==================================================
@staff_member_required
def admin_export_abstracts(request):
    user = request.user
    abstracts = _get_theme_filtered_abstracts(user)

    if abstracts is None:
        return HttpResponseForbidden("Not authorized.")

    # Apply same filters as list view so export matches current view
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("search", "")
    theme_filter = request.GET.get("theme", "")

    if status_filter:
        abstracts = abstracts.filter(status=status_filter)

    if search_query:
        abstracts = abstracts.filter(
            Q(title__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    if theme_filter:
        abstracts = abstracts.filter(theme__code=theme_filter)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="abstracts.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Participant Code", "Title", "Author", "Email",
        "Theme", "Status", "Submitted On"
    ])

    for a in abstracts:
        writer.writerow([
            a.id,
            (getattr(getattr(a.user, 'participant', None), 'participant_code', '') or ''),
            a.title,
            a.user.get_full_name() or a.user.username,
            a.user.email,
            a.theme.name,
            a.get_status_display(),
            a.submitted_at.strftime("%d-%m-%Y"),
        ])

    return response


# ==================================================
# REGISTRATIONS
# ==================================================
@staff_member_required
def admin_registrations(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    registrations = Participant.objects.select_related("user")

    search = request.GET.get("search", "")
    if search:
        registrations = registrations.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(organization__icontains=search)
        )

    return render(
        request,
        "admin/registrations_list.html",
        {"registrations": registrations}
    )



@staff_member_required
def admin_registration_detail(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    registration = get_object_or_404(
        Participant.objects.select_related("user"),
        pk=pk
    )

    abstracts = AbstractSubmission.objects.filter(
        user=registration.user
    )

    return render(
        request,
        "admin/registration_detail.html",
        {
            "registration": registration,
            "abstracts": abstracts,
        }
    )


# ==================================================
# ANALYTICS
# ==================================================
@staff_member_required
def admin_analytics(request):
    user = request.user
    abstracts = _get_theme_filtered_abstracts(user)

    if abstracts is None:
        return HttpResponseForbidden("Not authorized.")

    # ================= BASE COUNTS =================
    total_abstracts = abstracts.count()
    total_registrations = 0

    last_30_days = timezone.now() - timedelta(days=30)

    recent_abstracts = abstracts.filter(
        submitted_at__gte=last_30_days
    ).count()

    if user.is_superuser:
        recent_registrations = Participant.objects.filter(
            created_at__gte=last_30_days
        ).count()
        total_registrations = Participant.objects.count()
    else:
        themes = user.theme_admin.themes.all()

        recent_registrations = Participant.objects.filter(
            user__abstracts__theme__in=themes,
            created_at__gte=last_30_days
        ).distinct().count()

        total_registrations = Participant.objects.filter(
            user__abstracts__theme__in=themes
        ).distinct().count()

    # ================= ABSTRACT STATUS =================
    abstracts_by_status = (
        abstracts
        .values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )

    status_labels = [s["status"] for s in abstracts_by_status]
    status_counts = [s["count"] for s in abstracts_by_status]

    # ================= ABSTRACT THEME =================
    abstracts_by_theme = (
        abstracts
        .values(theme_name=F("theme__name"))
        .annotate(count=Count("id"))
        .order_by("theme_name")
    )

    theme_labels = [t["theme_name"] for t in abstracts_by_theme]
    theme_counts = [t["count"] for t in abstracts_by_theme]

    # ================= SCIENTIFIC THEME (PARTICIPANTS) =================
    scientific_theme_stats = (
        Participant.objects
        .filter(user__abstracts__in=abstracts)
        .distinct()
        .values("scientific_theme")
        .annotate(count=Count("id"))
    )

    scientific_theme_labels = [
        s["scientific_theme"] or "Unknown"
        for s in scientific_theme_stats
    ]
    scientific_theme_counts = [s["count"] for s in scientific_theme_stats]

    # ================= CONTEXT =================
    context = {
        "total_abstracts": total_abstracts,
        "total_registrations": total_registrations,
        "recent_abstracts": recent_abstracts,
        "recent_registrations": recent_registrations,

        "abstracts_by_status": abstracts_by_status,
        "abstracts_by_theme": abstracts_by_theme,

        # Chart.js
        "status_labels": json.dumps(status_labels),
        "status_counts": json.dumps(status_counts),
        "theme_labels": json.dumps(theme_labels),
        "theme_counts": json.dumps(theme_counts),

        "scientific_theme_labels": json.dumps(scientific_theme_labels),
        "scientific_theme_counts": json.dumps(scientific_theme_counts),
    }

    return render(request, "admin/analytics.html", context)


# ==================================================
# EXPORT REGISTRATIONS
# ==================================================
@staff_member_required
def admin_export_registrations(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registrations.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Username",
        "Participant Code",
        "Full Name",
        "Email",
        "Organization",
        "Designation",
        "Scientific Theme",
        "Phone",
        "Registered On",
    ])

    for p in Participant.objects.select_related("user"):
        writer.writerow([
            p.user.username,
            p.participant_code or "",
            p.user.get_full_name(),
            p.user.email,
            p.organization,
            p.designation,
            p.get_scientific_theme_display(),
            p.phone,
            p.created_at.strftime("%d-%m-%Y"),
        ])

    return response

# ==================================================
# THEME ADMIN MANAGEMENT (PARENT ADMIN ONLY)
# ==================================================

@staff_member_required
def theme_admin_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    theme_admins = ThemeAdmin.objects.select_related(
        "user"
    ).prefetch_related("themes")

    return render(
        request,
        "admin/theme_admin_list.html",
        {"theme_admins": theme_admins}
    )


@staff_member_required
def theme_admin_create(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    # Use registration page's canonical theme list (keeps admin UI consistent)
    try:
        reg = get_theme_choices(request).get('theme_choices', [])
    except Exception:
        reg = []
    themes = []
    if reg:
        for code, name in reg:
            st = ScientificTheme.objects.filter(code=code).first()
            if st:
                themes.append(st)
    if not themes:
        themes = ScientificTheme.objects.all()

    if request.method == "POST":
        email = request.POST.get("email").strip()
        password = request.POST.get("password")
        theme_ids = request.POST.getlist("themes")

        # ---- BASIC VALIDATION ----
        if not password or not theme_ids:
            messages.error(request, "Password and exactly one theme are required.")
            return redirect("conference:ncps_admin:theme_admin_create")

        # Enforce single-theme selection for theme admin
        if len(theme_ids) != 1:
            messages.error(request, "Please select exactly one scientific theme for a Theme Admin.")
            return redirect("conference:ncps_admin:theme_admin_create")

        # Derive username from selected theme name (slugified)
        from django.utils.text import slugify
        theme_obj = ScientificTheme.objects.filter(id=theme_ids[0]).first()
        if not theme_obj:
            messages.error(request, "Selected theme not found.")
            return redirect("conference:ncps_admin:theme_admin_create")

        # Prevent duplicate active ThemeAdmin for the same theme
        existing = ThemeAdmin.objects.filter(themes=theme_obj).exclude(user__isnull=True)
        if existing.exists():
            messages.error(request, f"A Theme Admin already exists for '{theme_obj.name}'. Remove or deactivate them first.")
            return redirect("conference:ncps_admin:theme_admin_create")

        base_username = slugify(theme_obj.name) or f"theme{theme_obj.id}"
        # sanitize (allow only letters, digits and underscore)
        import re as _re
        base_username = _re.sub(r"[^a-zA-Z0-9_]", "", base_username) or f"theme{theme_obj.id}"

        unique_username = base_username
        suffix = 1
        while User.objects.filter(username=unique_username).exists():
            unique_username = f"{base_username}{suffix}"
            suffix += 1
        username = unique_username

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
            return redirect("conference:ncps_admin:theme_admin_create")

        # ---- CREATE USER ----
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.is_staff = True          # ✅ REQUIRED
        user.is_superuser = False     # ❌ NEVER
        user.save()

        # ---- CREATE THEME ADMIN ----
        theme_admin = ThemeAdmin.objects.create(user=user)
        theme_admin.themes.set(theme_ids)

        messages.success(
            request,
            f"Theme Admin '{username}' created successfully."
        )
        log_admin_action(
            request,
            action="CREATE",
            obj=theme_admin,
            description=f"Theme admin {username} created"
        )

        return redirect("conference:ncps_admin:theme_admin_list")

    return render(
        request,
        "admin/theme_admin_create_ui.html",
        {"themes": themes}
    )
@staff_member_required
def theme_admin_edit(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    theme_admin = get_object_or_404(ThemeAdmin, pk=pk)
    # Use registration page's canonical theme list (keeps admin UI consistent)
    try:
        reg = get_theme_choices(request).get('theme_choices', [])
    except Exception:
        reg = []
    themes = []
    if reg:
        for code, name in reg:
            st = ScientificTheme.objects.filter(code=code).first()
            if st:
                themes.append(st)
    if not themes:
        themes = ScientificTheme.objects.all()

    if request.method == "POST":
        theme_ids = request.POST.getlist("themes")
        is_active = request.POST.get("is_active") == "on"
        # Prevent assigning a theme that already belongs to another ThemeAdmin
        if theme_ids:
            conflicts = (
                ThemeAdmin.objects
                .filter(themes__in=theme_ids)
                .exclude(pk=theme_admin.pk)
                .distinct()
            )
            if conflicts.exists():
                # find conflicting theme names
                conflict_theme_ids = set()
                for t in conflicts.prefetch_related('themes'):
                    for th in t.themes.all():
                        if str(th.id) in theme_ids:
                            conflict_theme_ids.add(th.id)
                bad_names = [ScientificTheme.objects.filter(id=i).first().name for i in conflict_theme_ids]
                messages.error(request, "The following themes are already assigned to other Theme Admins: " + ", ".join(bad_names))
                return redirect("conference:ncps_admin:theme_admin_edit", pk=pk)

        theme_admin.themes.set(theme_ids)
        theme_admin.is_active = is_active
        theme_admin.save()

        log_admin_action(
            request,
            action="UPDATE",
            obj=theme_admin,
            description="Theme admin updated"
        )

        messages.success(request, "Theme Admin updated.")
        return redirect("conference:ncps_admin:theme_admin_list")

    return render(
        request,
        "admin/theme_admin_form.html",
        {
            "theme_admin": theme_admin,
            "themes": themes,
            "mode": "edit",
        }
    )


@staff_member_required
def theme_admin_toggle(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    theme_admin = get_object_or_404(ThemeAdmin, pk=pk)
    theme_admin.is_active = not theme_admin.is_active
    theme_admin.save()
    log_admin_action(
        request,
        action="UPDATE",
        obj=theme_admin,
        description=f"Theme admin {'activated' if theme_admin.is_active else 'deactivated'}"
    )


    messages.success(request, "Theme Admin status updated.")
    return redirect("conference:ncps_admin:theme_admin_list")

@staff_member_required
def theme_admin_delete(request, pk):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    theme_admin = get_object_or_404(ThemeAdmin, pk=pk)
    user = theme_admin.user

    if request.method == "POST":
        # Remove admin role
        theme_admin.delete()

        # Revoke staff access
        user.is_staff = False
        user.save()

        messages.success(
            request,
            f"Theme admin access revoked for '{user.username}'."
        )
        log_admin_action(
            request,
            action="DELETE",
            obj=theme_admin,
            description="Theme admin removed"
        )

        return redirect("conference:ncps_admin:theme_admin_list")

    return render(
        request,
        "admin/theme_admin_confirm_delete.html",
        {"theme_admin": theme_admin}
    )




@staff_member_required
def theme_admin_dashboard(request):
    user = request.user

    # Safety check
    if not hasattr(user, "theme_admin") or not user.theme_admin.is_active:
        return HttpResponseForbidden("Not authorized")

    theme_admin = user.theme_admin
    themes_all = list(theme_admin.themes.all())

    # allow scoping the dashboard to a specific theme via ?theme=<id>
    theme_id = request.GET.get('theme')
    selected_theme = None
    if theme_id:
        try:
            sel = int(theme_id)
        except Exception:
            sel = None
        if sel:
            for t in themes_all:
                if t.id == sel:
                    selected_theme = t
                    break

    # default to first assigned theme when multiple exist
    if not selected_theme:
        selected_theme = themes_all[0] if themes_all else None

    # Abstracts belonging to the selected theme ONLY
    abstracts = AbstractSubmission.objects.filter(
        theme=selected_theme
    ).exclude(
        id__in=AbstractReview.objects.filter(
            reviewer=theme_admin
        ).values_list("abstract_id", flat=True)
    ) if selected_theme else AbstractSubmission.objects.none()

    # Abstracts assigned to this admin for review (show all assigned, not scoped)
    review_abstracts = (
        AbstractSubmission.objects
        .filter(
            reviews__reviewer=theme_admin
        )
        .select_related("theme")
        .prefetch_related(
            "reviews__assigned_by__user"
        )
        .distinct()
    )

    participants = Participant.objects.filter(
        user__abstracts__theme=selected_theme
    ).distinct() if selected_theme else Participant.objects.none()


    context = {
        "themes": themes_all,
        "selected_theme": selected_theme,

        # Selected theme stats
        "total_abstracts": abstracts.count(),
        "pending_count": abstracts.filter(status="PENDING").count(),
        "revision_count": abstracts.filter(status="REVISION").count(),
        "approved_count": abstracts.filter(status="APPROVED").count(),
        "rejected_count": abstracts.filter(status="REJECTED").count(),

        # Existing data (scoped)
        "abstracts": abstracts.order_by("-submitted_at")[:10],
        "participants": participants[:10],

        # notifications will be shown on dedicated page

        # review assignments scoped to selected theme
        "review_abstracts": review_abstracts,
    }

    return render(
        request,
        "admin/theme_dashboard.html",
        context
    )


@staff_member_required
def theme_admin_notifications(request):
    user = request.user

    # only active theme admins or superuser can access
    if not user.is_superuser and (not hasattr(user, "theme_admin") or not user.theme_admin.is_active):
        return HttpResponseForbidden("Not authorized")

    if request.method == "POST":
        # Mark single or all as read
        action = request.POST.get("action")
        if action == "mark_all":
            if user.is_superuser:
                Notification.objects.filter(is_read=False).update(is_read=True)
            else:
                Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        else:
            nid = request.POST.get("notification_id")
            if nid and nid.isdigit():
                # superuser may mark any notification; theme admins only theirs
                q = Notification.objects.filter(id=int(nid))
                if not user.is_superuser:
                    q = q.filter(user=user)
                q.update(is_read=True)

        return redirect("conference:ncps_admin:notifications")

    if user.is_superuser:
        notifications = Notification.objects.select_related("user", "abstract").order_by("-created_at")
        unread_count = Notification.objects.filter(is_read=False).count()
    else:
        notifications = Notification.objects.filter(user=user).order_by("-created_at")
        unread_count = notifications.filter(is_read=False).count()

    return render(
        request,
        "admin/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        }
    )

@staff_member_required
def assign_abstract_reviewer(request, pk):
    abstract = get_object_or_404(AbstractSubmission, pk=pk)
    user = request.user

    # Only theme admins can assign reviewers
    if not hasattr(user, "theme_admin") or not user.theme_admin.is_active:
        return HttpResponseForbidden("Not authorized")

    sender_admin = user.theme_admin

    if request.method != "POST":
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    reviewer_id = request.POST.get("reviewer")
    reviewer = get_object_or_404(ThemeAdmin, pk=reviewer_id)

    # Prevent self-assignment
    if reviewer == sender_admin:
        messages.error(request, "You cannot assign the review to yourself.")
        return redirect("conference:ncps_admin:abstract_detail", pk=pk)


    # ✅ Create or fetch review WITH assigned_by
    review, created = AbstractReview.objects.get_or_create(
        abstract=abstract,
        reviewer=reviewer,
        defaults={
            "assigned_by": sender_admin
        }
    )

    # 🔒 Backfill assigned_by if missing (old records)
    if review.assigned_by is None:
        review.assigned_by = sender_admin
        review.save(update_fields=["assigned_by"])

    if created:
        # 🔔 Notify reviewer
        Notification.objects.create(
            user=reviewer.user,
            abstract=abstract,
            title="Abstract Review Assigned",
            message=(
                f"You have been requested to review the abstract:\n\n"
                f"'{abstract.title}'"
            )
        )
        # Send email to reviewer
        try:
            if reviewer.user.email:
                send_mail(
                    subject="NCPS 2025 | Review Assignment",
                    message=(
                        f"Dear {reviewer.user.get_full_name() or reviewer.user.username},\n\n"
                        f"You have been assigned to review the abstract titled '{abstract.title}'.\n"
                        "Please log in to the admin dashboard to access the submission and submit your review.\n\n"
                        "Regards,\nNCPS 2025 Organizing Committee"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[reviewer.user.email],
                    fail_silently=True,
                )
        except Exception:
            pass

        # 🔔 Notify sender
        Notification.objects.create(
            user=sender_admin.user,
            abstract=abstract,
            title="Review Sent for Evaluation",
            message=(
                f"The abstract '{abstract.title}' has been sent to "
                f"{reviewer.user.get_full_name() or reviewer.user.username} "
                f"for review."
            )
        )
        # Optionally email the sender (confirmation)
        try:
            if sender_admin.user.email:
                send_mail(
                    subject="NCPS 2025 | Review Assigned",
                    message=(
                        f"Dear {sender_admin.user.get_full_name() or sender_admin.user.username},\n\n"
                        f"The abstract '{abstract.title}' was assigned to {reviewer.user.get_full_name() or reviewer.user.username} for review.\n\n"
                        "Regards,\nNCPS 2025 Organizing Committee"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[sender_admin.user.email],
                    fail_silently=True,
                )
        except Exception:
            pass

        log_admin_action(
            request,
            action="ASSIGN",
            obj=abstract,
            description=f"Reviewer {reviewer.user.username} assigned"
        )

        messages.success(request, "Reviewer assigned successfully.")
    else:
        messages.info(request, "This reviewer is already assigned.")

    return redirect("conference:ncps_admin:abstract_detail", pk=pk)


@staff_member_required
def submit_review_comment(request, pk):
    abstract = get_object_or_404(AbstractSubmission, pk=pk)
    user = request.user

    if not hasattr(user, "theme_admin"):
        return HttpResponseForbidden("Not authorized")

    theme_admin = user.theme_admin

    review = get_object_or_404(
        AbstractReview,
        abstract=abstract,
        reviewer=theme_admin
    )

    if request.method == "POST":
        review.status = request.POST.get("status")
        review.comment = request.POST.get("comment", "").strip()

        if review.is_submitted:
            review.edited_at = timezone.now()
        else:
            review.submitted_at = timezone.now()

        review.is_submitted = True
        review.save()

        # Notify the assigning theme admin that the reviewer has submitted/edited the review
        try:
            assigned_by = review.assigned_by
            if assigned_by and assigned_by.user:
                Notification.objects.create(
                    user=assigned_by.user,
                    abstract=abstract,
                    title="Review Submitted",
                    message=(
                        f"The reviewer {review.reviewer.user.get_full_name() or review.reviewer.user.username} "
                        f"has submitted a review for '{abstract.title}' (status: {review.status})."
                    ),
                )
                # send email to assigned_by
                try:
                    if assigned_by.user.email:
                        send_mail(
                            subject="NCPS 2025 | Review Submitted",
                            message=(
                                f"Dear {assigned_by.user.get_full_name() or assigned_by.user.username},\n\n"
                                f"The reviewer {review.reviewer.user.get_full_name() or review.reviewer.user.username} has submitted a review for the abstract '{abstract.title}' with status {review.status}.\n\n"
                                "Please log in to the admin dashboard to view the comments and take further action.\n\nRegards,\nNCPS 2025 Organizing Committee"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[assigned_by.user.email],
                            fail_silently=True,
                        )
                except Exception:
                    pass
        except Exception:
            pass

        log_admin_action(
            request,
            action="UPDATE",
            obj=abstract,
            description=f"Reviewer marked as {review.status}"
        )

        messages.success(
            request,
            "Review submitted successfully."
        )

    return redirect("conference:ncps_admin:abstract_detail", pk=pk)


@staff_member_required
def export_admin_logs(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only parent admin allowed.")

    logs = AdminActionLog.objects.select_related("user").order_by("-created_at")

    # SAME FILTERS AS LIST PAGE
    action = request.GET.get("action")
    user_id = request.GET.get("user")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if action:
        logs = logs.filter(action=action)

    if user_id:
        logs = logs.filter(user__id=user_id)

    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)

    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    # CSV RESPONSE
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="admin_logs.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Time",
        "User",
        "Action",
        "Object Type",
        "Object ID",
        "IP Address",
        "Description",
    ])

    for log in logs:
        writer.writerow([
            log.created_at.strftime("%d-%m-%Y %H:%M"),
            log.user.username if log.user else "System",
            log.get_action_display(),
            log.object_type or "",
            log.object_id or "",
            log.ip_address,
            log.description,
        ])

    return response
