from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from smartshelf.library.forms import BookForm
from smartshelf.library.models import Book, BorrowRecord, Fine

User = get_user_model()


def is_librarian(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_librarian)
def librarian_dashboard(request):
    """Main administrative dashboard with key metrics and active loans."""
    total_books = Book.objects.aggregate(total=Sum("total_copies"))["total"] or 0
    available_books = Book.objects.aggregate(avail=Sum("available_copies"))["avail"] or 0
    borrowed_books_count = BorrowRecord.objects.filter(status=BorrowRecord.Status.BORROWED).count()
    overdue_count = BorrowRecord.objects.filter(
        status=BorrowRecord.Status.BORROWED,
        due_date__lt=timezone.now().date(),
    ).count()
    unpaid_fines_total = (
        Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )
    total_users_count = User.objects.count()

    recent_records = BorrowRecord.objects.select_related("user", "book").order_by("-borrow_date")[:10]

    return render(
        request,
        "admin_app/dashboard.html",
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
    return render(request, "admin_app/book_manage.html", {"books": books})


@login_required
@user_passes_test(is_librarian)
def book_create(request):
    """Add a new book to the catalog."""
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f"Book '{book.title}' created successfully.")
            return redirect("admin_app:manage_books")
    else:
        form = BookForm()
    return render(request, "admin_app/book_form.html", {"form": form, "title": "Add New Book"})


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
            return redirect("admin_app:manage_books")
    else:
        form = BookForm(instance=book)
    return render(request, "admin_app/book_form.html", {"form": form, "title": f"Edit {book.title}"})


@login_required
@user_passes_test(is_librarian)
def book_delete(request, pk):
    """Delete a book."""
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        book.delete()
        messages.success(request, "Book deleted.")
        return redirect("admin_app:manage_books")
    return render(request, "admin_app/confirm_delete.html", {"object": book})


@login_required
@user_passes_test(is_librarian)
def manage_fines(request):
    """Admin fine collection and status tracking."""
    fines = Fine.objects.select_related("borrow_record__user", "borrow_record__book").order_by("-id")
    return render(request, "admin_app/fine_list.html", {"fines": fines})


@login_required
@user_passes_test(is_librarian)
def mark_fine_paid(request, fine_id):
    """Mark a fine as collected/paid."""
    fine = get_object_or_404(Fine, id=fine_id)
    fine.is_paid = True
    fine.paid_at = timezone.now()
    fine.save()
    messages.success(request, f"Fine of ${fine.amount} for {fine.borrow_record.user} marked as paid.")
    return redirect("admin_app:manage_fines")


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

    daily_fines = (
        Fine.objects.filter(paid_at__date=today, is_paid=True).aggregate(s=Sum("amount"))["s"]
        or Decimal("0.00")
    )
    monthly_fines = (
        Fine.objects.filter(paid_at__date__gte=month_ago, is_paid=True).aggregate(s=Sum("amount"))["s"]
        or Decimal("0.00")
    )

    return render(
        request,
        "admin_app/reports.html",
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
    return render(request, "admin_app/user_monitor.html", {"monitored_users": users})
