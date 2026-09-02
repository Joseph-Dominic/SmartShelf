from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AuthorForm, BookForm, CategoryForm, IssueBookForm
from .models import Author, Book, BorrowRecord, Category, Fine

User = get_user_model()


# ==========================================
# USER & CATALOG VIEWS
# ==========================================

def book_catalog(request):
    """Search and filter books by title, author, category, ISBN, and stock."""
    query = request.GET.get("q", "")
    category_id = request.GET.get("category", "")
    author_id = request.GET.get("author", "")
    available_only = request.GET.get("available", "")

    books = Book.objects.select_related("author", "category").all()

    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(isbn__icontains=query)
            | Q(author__name__icontains=query)
        )
    if category_id:
        books = books.filter(category_id=category_id)
    if author_id:
        books = books.filter(author_id=author_id)
    if available_only == "1":
        books = books.filter(available_copies__gt=0)

    categories = Category.objects.all()
    authors = Author.objects.all()

    return render(
        request,
        "library/book_list.html",
        {
            "books": books,
            "categories": categories,
            "authors": authors,
            "query": query,
            "selected_category": category_id,
            "selected_author": author_id,
            "available_only": available_only,
        },
    )


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related("author", "category"), pk=pk)
    user_active_borrow = False
    if request.user.is_authenticated:
        user_active_borrow = BorrowRecord.objects.filter(
            user=request.user,
            book=book,
            status__in=[BorrowRecord.Status.BORROWED, BorrowRecord.Status.OVERDUE],
        ).exists()

    return render(
        request,
        "library/book_detail.html",
        {"book": book, "user_active_borrow": user_active_borrow},
    )


@login_required
@transaction.atomic
def borrow_book(request, pk):
    """User borrow action."""
    book = get_object_or_404(Book, pk=pk)

    if book.available_copies < 1:
        messages.error(request, f"'{book.title}' has no copies currently available.")
        return redirect("library:book_detail", pk=pk)

    active_borrow = BorrowRecord.objects.filter(
        user=request.user,
        book=book,
        status__in=[BorrowRecord.Status.BORROWED, BorrowRecord.Status.OVERDUE],
    ).exists()

    if active_borrow:
        messages.warning(request, "You already have an active loan for this book.")
        return redirect("library:book_detail", pk=pk)

    due_date = timezone.now().date() + timedelta(days=14)
    BorrowRecord.objects.create(user=request.user, book=book, due_date=due_date)

    book.available_copies -= 1
    book.save()

    messages.success(request, f"Successfully borrowed '{book.title}'. Return by {due_date}.")
    return redirect("library:user_loans")


@login_required
@transaction.atomic
def return_book(request, record_id):
    """User return action with automatic fine calculation."""
    record = get_object_or_404(BorrowRecord, id=record_id, user=request.user)

    if record.status == BorrowRecord.Status.RETURNED:
        messages.info(request, "This book has already been returned.")
        return redirect("library:user_loans")

    record.return_date = timezone.now().date()
    record.status = BorrowRecord.Status.RETURNED
    record.save()

    record.book.available_copies += 1
    record.book.save()

    fine_amount = record.calculate_fine()
    if fine_amount > Decimal("0.00"):
        Fine.objects.get_or_create(borrow_record=record, defaults={"amount": fine_amount})
        messages.warning(request, f"Book returned overdue. Fine generated: ${fine_amount}.")
    else:
        messages.success(request, f"'{record.book.title}' was successfully returned.")

    return redirect("library:user_loans")


@login_required
def user_loans(request):
    """User loans dashboard with history, fines, and personalized recommendations."""
    records = BorrowRecord.objects.filter(user=request.user).select_related("book", "fine")
    active_loans = records.filter(status__in=[BorrowRecord.Status.BORROWED, BorrowRecord.Status.OVERDUE])
    history = records.filter(status=BorrowRecord.Status.RETURNED)

    # Content-based recommendation algorithm
    borrowed_category_ids = (
        records.values_list("book__category", flat=True).distinct()
    )
    already_borrowed_ids = records.values_list("book_id", flat=True)

    recommendations = (
        Book.objects.filter(category__in=borrowed_category_ids)
        .exclude(id__in=already_borrowed_ids)
        .select_related("author", "category")[:4]
    )

    return render(
        request,
        "library/user_loans.html",
        {
            "active_loans": active_loans,
            "history": history,
            "recommendations": recommendations,
        },
    )

