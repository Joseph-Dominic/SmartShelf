from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """Custom email-login user model for SmartShelf."""

    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    class Role(models.TextChoices):
        ADMIN = "ADMIN", _("Librarian / Admin")
        STAFF = "STAFF", _("Faculty / Staff")
        STUDENT_PG = "STUDENT_PG", _("Postgraduate (PG)")
        STUDENT_UG = "STUDENT_UG", _("Undergraduate (UG)")

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT_UG,
        help_text=_("Designates borrowing quotas and renewal permissions."),
    )
    member_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text=_("Roll number for students or Employee ID for staff."),
    )
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: UserManager = UserManager()

    @property
    def is_librarian(self):
        return self.is_superuser or self.role == self.Role.ADMIN or self.is_staff

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.pk})

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"