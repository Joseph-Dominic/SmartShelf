from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Subject(models.Model):
    name = models.CharField(_("Subject Name"), max_length=120, unique=True)
    code = models.CharField(_("Subject Code"), max_length=20, unique=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


Category = Subject  # Alias for backward compatibility


class Author(models.Model):
    name = models.CharField(_("Author Name"), max_length=255)
    biography = models.TextField(_("Biography"), blank=True)

    class Meta:
        verbose_name = _("Author")
        verbose_name_plural = _("Authors")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(_("Book Title"), max_length=255)
    isbn = models.CharField(_("ISBN"), max_length=20, unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books", verbose_name=_("Author"))
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="books", verbose_name=_("Subject"), null=True, blank=True
    )
    edition = models.CharField(_("Edition"), max_length=50, blank=True)
    publisher = models.CharField(_("Publisher"), max_length=255, blank=True)
    description = models.TextField(_("Description"), blank=True)
    cover_image = models.ImageField(_("Cover Image"), upload_to="book_covers/", blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Book")
        verbose_name_plural = _("Books")
        ordering = ["title"]

    def __str__(self):
        return f"{self.title} ({self.isbn})"

    def get_absolute_url(self):
        return reverse("library:book_detail", kwargs={"pk": self.pk})

    @property
    def total_copies(self):
        return self.copies.count()

    @property
    def available_copies(self):
        return self.copies.filter(status=BookCopy.Status.AVAILABLE).count()

    @property
    def is_available(self):
        return self.available_copies > 0


class BookCopy(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Available")
        ISSUED = "ISSUED", _("Issued")
        RESERVED = "RESERVED", _("Reserved")
        MAINTENANCE = "MAINTENANCE", _("Under Maintenance")
        LOST = "LOST", _("Lost")

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies", verbose_name=_("Book"))
    accession_number = models.CharField(
        _("Accession / Barcode Number"),
        max_length=50,
        unique=True,
        help_text=_("Unique physical barcode attached to the copy.")
    )
    shelf_location = models.CharField(_("Shelf Location"), max_length=50, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        verbose_name = _("Physical Book Copy")
        verbose_name_plural = _("Physical Book Copies")
        ordering = ["accession_number"]

    def __str__(self):
        return f"{self.book.title} [Copy: {self.accession_number}]"


class BorrowingPolicy(models.Model):
    ROLE_CHOICES = (
        ("STAFF", "Faculty / Staff"),
        ("STUDENT_PG", "Postgraduate Student (PG)"),
        ("STUDENT_UG", "Undergraduate Student (UG)"),
    )

    role = models.CharField(_("Academic Role"), max_length=20, choices=ROLE_CHOICES, unique=True)
    max_books = models.PositiveIntegerField(_("Max Books Allowed"), default=3)
    loan_duration_days = models.PositiveIntegerField(_("Loan Duration (Days)"), default=14)
    max_renewals = models.PositiveIntegerField(_("Max Renewals Permitted"), default=2)
    daily_fine_rate = models.DecimalField(
        _("Daily Fine Rate"), max_digits=6, decimal_places=2, default=Decimal("5.00")
    )

    class Meta:
        verbose_name = _("Borrowing Policy")
        verbose_name_plural = _("Borrowing Policies")

    def __str__(self):
        return f"Policy for {self.get_role_display()}"


class Loan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        RETURNED = "RETURNED", _("Returned")
        OVERDUE = "OVERDUE", _("Overdue")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loans", verbose_name=_("User")
    )
    book_copy = models.ForeignKey(
        BookCopy, on_delete=models.PROTECT, related_name="loans", verbose_name=_("Physical Copy")
    )
    issue_date = models.DateField(_("Issue Date"), default=timezone.now)
    due_date = models.DateField(_("Due Date"))
    return_date = models.DateField(_("Return Date"), null=True, blank=True)
    renewal_count = models.PositiveIntegerField(_("Renewal Count"), default=0)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        verbose_name = _("Loan")
        verbose_name_plural = _("Loans")
        ordering = ["-issue_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["book_copy"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_loan_per_physical_copy",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.book_copy.book.title} ({self.status})"

    @property
    def overdue_days(self):
        end_date = self.return_date or timezone.now().date()
        if end_date > self.due_date:
            return (end_date - self.due_date).days
        return 0

    @property
    def current_fine(self):
        if self.overdue_days <= 0:
            return Decimal("0.00")
        user_role = getattr(self.user, "role", "STUDENT_UG")
        policy = BorrowingPolicy.objects.filter(role=user_role).first()
        rate = policy.daily_fine_rate if policy else Decimal("5.00")
        return Decimal(self.overdue_days) * rate

    def save(self, *args, **kwargs):
        if not self.due_date:
            user_role = getattr(self.user, "role", "STUDENT_UG")
            policy = BorrowingPolicy.objects.filter(role=user_role).first()
            duration = policy.loan_duration_days if policy else 14
            self.due_date = timezone.now().date() + timedelta(days=duration)
        super().save(*args, **kwargs)


BorrowRecord = Loan  # Backward compatibility alias


class Fine(models.Model):
    loan = models.OneToOneField(
        Loan,
        on_delete=models.CASCADE,
        related_name="fine",
        verbose_name=_("Loan"),
        null=True,
        blank=True,
    )
    amount = models.DecimalField(_("Fine Amount"), max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(_("Paid Status"), default=False)
    paid_at = models.DateTimeField(_("Payment Date"), null=True, blank=True)
    cleared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_fines",
        verbose_name=_("Cleared By (Staff)")
    )

    class Meta:
        verbose_name = _("Fine")
        verbose_name_plural = _("Fines")

    def __str__(self):
        return f"Fine: ₹{self.amount} for {self.loan}"


class Reservation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations", verbose_name=_("User")
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="reservations", verbose_name=_("Book")
    )
    reserved_at = models.DateTimeField(_("Reserved At"), auto_now_add=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        ordering = ["reserved_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=models.Q(is_active=True),
                name="unique_active_user_book_reservation",
            )
        ]

    def __str__(self):
        return f"Hold on '{self.book.title}' by {self.user}"