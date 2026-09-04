from django.contrib import admin
from .models import (
    Subject,
    Author,
    Book,
    BookCopy,
    BorrowingPolicy,
    Loan,
    Fine,
    Reservation,
)


class BookCopyInline(admin.TabularInline):
    """Enables adding/editing physical copies directly on the Book edit page."""
    model = BookCopy
    extra = 1
    fields = ("accession_number", "shelf_location", "status")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "book_count")
    search_fields = ("code", "name")

    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = "Titles"


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn", "author", "subject", "available_copies_count", "total_copies_count")
    list_filter = ("subject", "author")
    search_fields = ("title", "isbn", "author__name")
    inlines = [BookCopyInline]

    def available_copies_count(self, obj):
        return obj.copies.filter(status=BookCopy.Status.AVAILABLE).count()
    available_copies_count.short_description = "Available Copies"

    def total_copies_count(self, obj):
        return obj.copies.count()
    total_copies_count.short_description = "Total Copies"


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ("accession_number", "book", "shelf_location", "status")
    list_filter = ("status", "shelf_location")
    search_fields = ("accession_number", "book__title", "book__isbn")


@admin.register(BorrowingPolicy)
class BorrowingPolicyAdmin(admin.ModelAdmin):
    list_display = ("role", "max_books", "loan_duration_days", "max_renewals", "daily_fine_rate")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "get_book_title", "get_accession_number", "issue_date", "due_date", "renewal_count", "status")
    list_filter = ("status", "issue_date", "due_date")
    search_fields = ("user__username", "user__email", "user__member_id", "book_copy__accession_number", "book_copy__book__title")
    readonly_fields = ("issue_date",)

    def get_book_title(self, obj):
        return obj.book_copy.book.title
    get_book_title.short_description = "Book Title"

    def get_accession_number(self, obj):
        return obj.book_copy.accession_number
    get_accession_number.short_description = "Barcode / Copy ID"


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("get_borrower", "amount", "is_paid", "paid_date", "cleared_by")
    list_filter = ("is_paid", "paid_date")
    search_fields = ("loan__user__username", "loan__user__member_id")
    actions = ["mark_as_paid"]

    def get_borrower(self, obj):
        return obj.loan.user
    get_borrower.short_description = "Borrower"

    @admin.action(description="Mark selected fines as paid")
    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True, cleared_by=request.user)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "reserved_at", "is_active")
    list_filter = ("is_active", "reserved_at")
    search_fields = ("book__title", "user__username", "user__member_id")