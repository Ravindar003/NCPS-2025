from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import AbstractSubmission, ThemeAdmin, Notification


@receiver(pre_save, sender=AbstractSubmission)
def abstract_decision_email(sender, instance, **kwargs):
    # New submission → no email
    if not instance.pk:
        return

    try:
        old = AbstractSubmission.objects.get(pk=instance.pk)
    except AbstractSubmission.DoesNotExist:
        return

    # No change → no email
    if old.status == instance.status:
        return

    user = instance.user
    if not user.email:
        return

    # ---------------- EMAIL CONTENT ----------------
    name = user.get_full_name() or user.username
    title = instance.title
    decision = instance.status

    # Subject & body based on decision
    if decision == "APPROVED":
        subject = "NCPS 2025 | Abstract Approved"
        body = f"""
Dear {name},

We are pleased to inform you that your submitted abstract titled
"{title}" has been approved for NCPS 2025.

Further details regarding presentation guidelines and schedules
will be shared in due course through your dashboard.

Thank you for your valuable contribution to NCPS 2025.

Warm regards,
NCPS 2025 Organizing Committee
"""

    elif decision == "REVISION":
        subject = "NCPS 2025 | Revision Required for Abstract"
        body = f"""
Dear {name},

Thank you for submitting your abstract titled
"{title}" to NCPS 2025.

Based on the review, revisions are required before further
consideration. We kindly request you to log in to your dashboard
to review the comments and submit the revised version within
the specified deadline.

Warm regards,
NCPS 2025 Organizing Committee
"""

    elif decision == "REJECTED":
        subject = "NCPS 2025 | Abstract Decision"
        body = f"""
Dear {name},

Thank you for your interest in NCPS 2025.

After careful evaluation, we regret to inform you that your
abstract titled "{title}" was not approved for this year's
conference.

We appreciate your effort and encourage you to participate
in future editions of NCPS.

Warm regards,
NCPS 2025 Organizing Committee
"""

    else:
        # For other internal transitions (recommended, resubmitted, etc.)
        subject = "NCPS 2025 | Update on Your Abstract"
        body = f"""
Dear {name},

There has been an update regarding your abstract titled
"{title}".

Please log in to your NCPS dashboard for further details.

Warm regards,
NCPS 2025 Organizing Committee
"""

    send_mail(
        subject=subject,
        message=body.strip(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

    # Notify theme admins about the decision
    try:
        theme = instance.theme
        admins = ThemeAdmin.objects.filter(themes=theme, is_active=True)
        for ta in admins:
            # create a lightweight notification
            Notification.objects.create(
                user=ta.user,
                abstract=instance,
                title=f"Abstract decision: {decision}",
                message=(
                    f"The abstract '{instance.title}' has changed status to {decision}."
                ),
            )
    except Exception:
        pass


@receiver(post_save, sender=AbstractSubmission)
def abstract_created_notify_theme_admins(sender, instance, created, **kwargs):
    """Notify active ThemeAdmins when a new abstract is submitted for their theme."""
    if not created:
        return
    try:
        theme = instance.theme
        admins = ThemeAdmin.objects.filter(themes=theme, is_active=True)
        for ta in admins:
            Notification.objects.create(
                user=ta.user,
                abstract=instance,
                title="New abstract submitted",
                message=(f"A new abstract titled '{instance.title}' was submitted under '{theme.name}'."),
            )
        # Send confirmation email to the submitting participant
        try:
            submitter = instance.user
            if submitter.email:
                subject = "NCPS 2025 | Abstract Submitted"
                body = f"""
    Dear {submitter.get_full_name() or submitter.username},

    We have received your abstract titled "{instance.title}" submitted to NCPS 2025.
    Your submission is now in the review queue. You will be notified by email when a decision is made or if revisions are requested.

    Thank you for your submission.

    NCPS 2025 Organizing Committee
    """
                send_mail(
                    subject=subject,
                    message=body.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[submitter.email],
                    fail_silently=True,
                )
        except Exception:
            pass
    except Exception:
        pass
