from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
import string
import random
import os
import time


# ==================================================
# PARTICIPANT
# ==================================================
class Participant(models.Model):

    SCIENTIFIC_THEMES = [
        ("climate_change", "Climate Change"),
        ("polar_biology", "Polar Biology"),
        ("glaciology", "Glaciology"),
        ("oceanography", "Oceanography"),
        ("atmospheric_science", "Atmospheric Science"),
        ("remote_sensing", "Remote Sensing"),
        ("polar_geology", "Polar Geology"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="participant"
    )
    organization = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)

    # Honorific / Title (Mr, Mrs, Dr, Prof, etc.)
    TITLE_CHOICES = [
        ("", ""),
        ("Mr", "Mr"),
        ("Mrs", "Mrs"),
        ("Ms", "Ms"),
        ("Dr", "Dr"),
        ("Prof", "Prof"),
        ("Mx", "Mx"),
        ("Other", "Other"),
    ]

    title = models.CharField(max_length=20, choices=TITLE_CHOICES, blank=True, null=True)

    scientific_theme = models.CharField(
        max_length=50,
        choices=SCIENTIFIC_THEMES,
        default="other"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Unique participant code shown across the site (e.g. CC-A1B2C3)
    participant_code = models.CharField(max_length=16, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.organization})"

    def _theme_prefix(self):
        """Return a short prefix for the scientific theme."""
        mapping = {
            "climate_change": "CC",
            "polar_biology": "PB",
            "glaciology": "GL",
            "oceanography": "OC",
            "atmospheric_science": "AS",
            "remote_sensing": "RS",
            "polar_geology": "PG",
            "other": "OT",
        }
        return mapping.get(self.scientific_theme, "OT")

    def _generate_code(self, length=6):
        """Generate a unique alphanumeric code with theme prefix."""
        prefix = self._theme_prefix()
        # Use uppercase letters and digits
        chars = string.ascii_uppercase + string.digits

        for _ in range(10):
            rand = get_random_string(length, allowed_chars=chars)
            code = f"{prefix}-{rand}"
            if not self.__class__.objects.filter(participant_code=code).exists():
                return code
        # Fallback: timestamp-based code
        ts = int(time.time())
        return f"{prefix}-{ts}"

    def save(self, *args, **kwargs):
        # Ensure a participant_code exists
        if not self.participant_code:
            self.participant_code = self._generate_code()
        super().save(*args, **kwargs)


# ==================================================
# SCIENTIFIC THEME (ADMIN CONTROLLED)
# ==================================================
class ScientificTheme(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ==================================================
# ABSTRACT SUBMISSION
# ==================================================
def submission_upload_path(instance, filename):
    ts = int(time.time())
    safe_name = filename.replace(" ", "_")
    return os.path.join(
        "abstracts",
        f"{instance.user.username}_{ts}_{safe_name}"
    )


from django.core.exceptions import ValidationError
import re

class AbstractSubmission(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("REVISION", "Revision Required"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="abstracts"
    )

    title = models.CharField(max_length=255)

    abstract = models.TextField(
        blank=True,
        null=True
    )

    theme = models.ForeignKey(
        ScientificTheme,
        on_delete=models.PROTECT,
        related_name="abstracts"
    )

    pdf_file = models.FileField(
        upload_to=submission_upload_path,
        blank=True,
        null=True
    )

    revised_submission = models.FileField(
        upload_to=submission_upload_path,
        blank=True,
        null=True
    )

    revised_uploaded_at = models.DateTimeField(
        blank=True,
        null=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    admin_comments = models.TextField(
        blank=True,
        null=True
    )

    revision_due_date = models.DateField(
        blank=True,
        null=True
    )

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_abstracts"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.title} — {self.user.username}"

    # ==================================================
    # MODEL VALIDATION (SINGLE SOURCE OF TRUTH)
    # ==================================================
    def clean(self):
        errors = {}

        # Enforce PDF-only submissions (text abstracts removed from workflow)
        has_pdf = bool(self.pdf_file)

        if not has_pdf:
            errors["pdf_file"] = "You must upload a PDF file for the abstract."

        # Ensure revised submission is a PDF when provided
        if self.revised_submission and not self.revised_submission.name.lower().endswith('.pdf'):
            errors["revised_submission"] = (
                "Revised submissions must be uploaded as a PDF file."
            )

        if errors:
            raise ValidationError(errors)

    # ==================================================
    # FORCE VALIDATION ON EVERY SAVE
    # ==================================================
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# ==================================================
# THEME ADMIN
# ==================================================
class ThemeAdmin(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="theme_admin"
    )

    themes = models.ManyToManyField(
        ScientificTheme,
        related_name="theme_admins"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    abstract = models.ForeignKey(
        AbstractSubmission,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class AbstractReview(models.Model):

    REVIEW_CHOICES = [
        ("APPROVED", "Approve"),
        ("REVISION", "Revision Required"),
        ("REJECTED", "Reject"),
    ]

    abstract = models.ForeignKey(
        AbstractSubmission,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    reviewer = models.ForeignKey(
        ThemeAdmin,
        on_delete=models.CASCADE,
        related_name="assigned_reviews"
    )

    # ✅ NEW: who assigned the review
    assigned_by = models.ForeignKey(
        ThemeAdmin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_reviews"
    )

    status = models.CharField(
        max_length=20,
        choices=REVIEW_CHOICES,
        blank=True,
        null=True
    )

    comment = models.TextField(blank=True)
    is_submitted = models.BooleanField(default=False)

    submitted_at = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("abstract", "reviewer")

# ==================================================
# ADMIN ACTION LOG
# ==================================================
class AdminActionLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ASSIGN", "Assign Reviewer"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("OTHER", "Other"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_logs"
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    object_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    object_id = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    description = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))

    def __str__(self):
        return f"{self.user.email} - {self.otp}"
