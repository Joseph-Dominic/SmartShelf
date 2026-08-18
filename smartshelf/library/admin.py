from django.contrib import admin
from .models import Author, Book, BorrowRecord, Category, Fine


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn", "author", "category", "available_copies", "total_copies")
    list_filter = ("category", "author")
    search_fields = ("title", "isbn", "author__name")


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "borrow_date", "due_date", "return_date", "status")
    list_filter = ("status", "borrow_date", "due_date")
    search_fields = ("user__email", "book__title")


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("borrow_record", "amount", "is_paid", "paid_at")
    list_filter = ("is_paid",)