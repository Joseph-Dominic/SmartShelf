from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AuthorForm, BookForm, CategoryForm, IssueBookForm
from .models import Author, Book, BorrowRecord, Category, Fine

User = get_user_model()


def is_librarian(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


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


# ==========================================
# ADMIN / LIBRARIAN VIEWS
# ==========================================

@login_required
@user_passes_test(is_librarian)
def librarian_dashboard(request):
    """Main administrative dashboard with key metrics and active loans."""
    total_books = Book.objects.aggregate(total=Sum("total_copies"))["total"] or 0
    available_books = Book.objects.aggregate(avail=Sum("available_copies"))["avail"] or 0
    borrowed_books_count = BorrowRecord.objects.filter(status=BorrowRecord.Status.BORROWED).count()
    overdue_count = BorrowRecord.objects.filter(
        status=BorrowRecord.Status.BORROWED, due_date__lt=timezone.now().date()
    ).count()
    unpaid_fines_total = (
        Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )
    total_users_count = User.objects.count()

    recent_records = BorrowRecord.objects.select_related("user", "book").order_by("-borrow_date")[:10]

    return render(
        request,
        "library/admin/dashboard.html",
        {
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books_count": borrowed_books_count,
            "overdue_count": overdue_count,
            "unpaid_fines_total": unpaid_fines_total,
            "total_users_count": total_users_count,
            "recent_records": recent_records,
        },
    )


@login_required
@user_passes_test(is_librarian)
def manage_books(request):
    """Admin book management list."""
    books = Book.objects.select_related("author", "category").all()
    return render(request, "library/admin/book_manage.html", {"books": books})


@login_required
@user_passes_test(is_librarian)
def book_create(request):
    """Add a new book to the catalog."""
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f"Book '{book.title}' created successfully.")
            return redirect("library:manage_books")
    else:
        form = BookForm()
    return render(request, "library/admin/book_form.html", {"form": form, "title": "Add New Book"})


@login_required
@user_passes_test(is_librarian)
def book_update(request, pk):
    """Edit existing book details."""
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f"Book '{book.title}' updated.")
            return redirect("library:manage_books")
    else:
        form = BookForm(instance=book)
    return render(request, "library/admin/book_form.html", {"form": form, "title": f"Edit {book.title}"})


@login_required
@user_passes_test(is_librarian)
def book_delete(request, pk):
    """Delete a book."""
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        book.delete()
        messages.success(request, "Book deleted.")
        return redirect("library:manage_books")
    return render(request, "library/admin/confirm_delete.html", {"object": book})


@login_required
@user_passes_test(is_librarian)
def manage_fines(request):
    """Admin fine collection and status tracking."""
    fines = Fine.objects.select_related("borrow_record__user", "borrow_record__book").order_by("-id")
    return render(request, "library/admin/fine_list.html", {"fines": fines})


@login_required
@user_passes_test(is_librarian)
def mark_fine_paid(request, fine_id):
    """Mark a fine as collected/paid."""
    fine = get_object_or_404(Fine, id=fine_id)
    fine.is_paid = True
    fine.paid_at = timezone.now()
    fine.save()
    messages.success(request, f"Fine of ${fine.amount} for {fine.borrow_record.user} marked as paid.")
    return redirect("library:manage_fines")


@login_required
@user_passes_test(is_librarian)
def reports_view(request):
    """Generate daily, weekly, and monthly borrowing reports."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    daily_loans = BorrowRecord.objects.filter(borrow_date=today).count()
    weekly_loans = BorrowRecord.objects.filter(borrow_date__gte=week_ago).count()
    monthly_loans = BorrowRecord.objects.filter(borrow_date__gte=month_ago).count()

    daily_fines = Fine.objects.filter(paid_at__date=today, is_paid=True).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
    monthly_fines = Fine.objects.filter(paid_at__date__gte=month_ago, is_paid=True).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

    return render(
        request,
        "library/admin/reports.html",
        {
            "daily_loans": daily_loans,
            "weekly_loans": weekly_loans,
            "monthly_loans": monthly_loans,
            "daily_fines": daily_fines,
            "monthly_fines": monthly_fines,
        },
    )


@login_required
@user_passes_test(is_librarian)
def monitor_users(request):
    """Monitor registered users and their loan activities."""
    users = User.objects.annotate(
        total_borrowed=Count("borrow_records"),
        active_loans=Count("borrow_records", filter=Q(borrow_records__status=BorrowRecord.Status.BORROWED)),
    ).order_by("-date_joined")
    return render(request, "library/admin/user_monitor.html", {"monitored_users": users})