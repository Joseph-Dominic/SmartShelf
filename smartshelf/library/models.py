from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(_("Category Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


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
    isbn = models.CharField(_("ISBN"), max_length=13, unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books", verbose_name=_("Author"))
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="books", verbose_name=_("Category")
    )
    description = models.TextField(_("Description"), blank=True)
    total_copies = models.PositiveIntegerField(_("Total Copies"), default=1)
    available_copies = models.PositiveIntegerField(_("Available Copies"), default=1)
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
    def is_available(self):
        return self.available_copies > 0


class BorrowRecord(models.Model):
    class Status(models.TextChoices):
        BORROWED = "BORROWED", _("Borrowed")
        RETURNED = "RETURNED", _("Returned")
        OVERDUE = "OVERDUE", _("Overdue")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrow_records", verbose_name=_("User")
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrow_records", verbose_name=_("Book"))
    borrow_date = models.DateField(_("Borrow Date"), default=timezone.now)
    due_date = models.DateField(_("Due Date"))
    return_date = models.DateField(_("Return Date"), null=True, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.BORROWED)

    class Meta:
        verbose_name = _("Borrow Record")
        verbose_name_plural = _("Borrow Records")
        ordering = ["-borrow_date"]

    def __str__(self):
        return f"{self.user} - {self.book.title} ({self.status})"

    def calculate_fine(self, rate_per_day=Decimal("2.00")):
        """Calculates overdue fine based on due date."""
        end_date = self.return_date or timezone.now().date()
        if end_date > self.due_date:
            days_overdue = (end_date - self.due_date).days
            return Decimal(days_overdue) * rate_per_day
        return Decimal("0.00")


class Fine(models.Model):
    borrow_record = models.OneToOneField(
        BorrowRecord, on_delete=models.CASCADE, related_name="fine", verbose_name=_("Borrow Record")
    )
    amount = models.DecimalField(_("Fine Amount ($)"), max_digits=8, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(_("Paid Status"), default=False)
    paid_at = models.DateTimeField(_("Payment Date"), null=True, blank=True)

    class Meta:
        verbose_name = _("Fine")
        verbose_name_plural = _("Fines")

    def __str__(self):
        return f"Fine: ${self.amount} for {self.borrow_record}"