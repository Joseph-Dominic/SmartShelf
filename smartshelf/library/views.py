from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import BookCopyForm, BookForm, IssueBookForm
from .models import Book, BookCopy, BorrowingPolicy, Fine, Loan, Reservation, Subject

User = get_user_model()


def librarian_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("account_login")
        if not getattr(request.user, "is_librarian", False):
            raise PermissionDenied(_("Access restricted to library staff."))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==========================================
# Catalog & Public Views
# ==========================================

def book_list_view(request):
    query = request.GET.get("q", "").strip()
    subject_id = request.GET.get("subject", "").strip()
    books = Book.objects.select_related("author", "subject").prefetch_related("copies").all()

    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(isbn__icontains=query) | Q(author__name__icontains=query)
        )
    if subject_id:
        books = books.filter(subject_id=subject_id)

    return render(
        request,
        "library/book_list.html",
        {"books": books, "subjects": Subject.objects.all(), "query": query, "selected_subject": subject_id},
    )


def book_detail_view(request, pk):
    book = get_object_or_404(Book.objects.select_related("author", "subject").prefetch_related("copies"), pk=pk)
    has_active_reservation = False
    if request.user.is_authenticated:
        has_active_reservation = Reservation.objects.filter(user=request.user, book=book, is_active=True).exists()
    return render(request, "library/book_detail.html", {"book": book, "has_active_reservation": has_active_reservation})


@login_required
@require_POST
def place_reservation_view(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if book.available_copies > 0:
        messages.warning(request, _("Copies are available on shelf. No reservation required."))
        return redirect("library:book_detail", pk=pk)

    reservation, created = Reservation.objects.get_or_create(user=request.user, book=book, is_active=True)
    if created:
        messages.success(request, _("Reservation placed successfully."))
    else:
        messages.info(request, _("You already hold an active reservation for this title."))
    return redirect("library:book_detail", pk=pk)


@login_required
@require_POST
def cancel_reservation_view(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, user=request.user, is_active=True)
    reservation.is_active = False
    reservation.save()
    messages.success(request, _("Reservation canceled."))
    return redirect("library:user_loans")


# ==========================================
# Borrower Portal
# ==========================================

@login_required
def user_loans_view(request):
    all_loans = Loan.objects.filter(user=request.user).select_related("book_copy__book", "book_copy__book__author")
    active_loans = all_loans.filter(status=Loan.Status.ACTIVE).order_by("due_date")
    returned_loans = all_loans.filter(status=Loan.Status.RETURNED).order_by("-return_date")[:10]
    reservations = Reservation.objects.filter(user=request.user, is_active=True).select_related("book")
    unpaid_fines = Fine.objects.filter(loan__user=request.user, is_paid=False).select_related("loan__book_copy__book")

    policy = BorrowingPolicy.objects.filter(role=request.user.role).first()
    max_books = policy.max_books if policy else 3

    return render(
        request,
        "library/user_loans.html",
        {
            "loans": active_loans,
            "loan_history": returned_loans,
            "reservations": reservations,
            "unpaid_fines": unpaid_fines,
            "policy": policy,
            "active_loans_count": active_loans.count(),
            "remaining_quota": max(0, max_books - active_loans.count()),
        },
    )


@login_required
@require_POST
def renew_loan_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user, status=Loan.Status.ACTIVE)
    policy = BorrowingPolicy.objects.filter(role=request.user.role).first()
    max_renewals = policy.max_renewals if policy else 2
    duration_days = policy.loan_duration_days if policy else 14

    if loan.due_date < timezone.now().date():
        messages.error(request, _("Overdue loans cannot be renewed. Return to circulation desk."))
        return redirect("library:user_loans")
    if loan.renewal_count >= max_renewals:
        messages.error(request, _("Maximum renewal limit reached."))
        return redirect("library:user_loans")
    if Fine.objects.filter(loan__user=request.user, is_paid=False).exists():
        messages.error(request, _("Clear outstanding fines before requesting renewals."))
        return redirect("library:user_loans")
    if Reservation.objects.filter(book=loan.book_copy.book, is_active=True).exclude(user=request.user).exists():
        messages.error(request, _("Cannot renew: item has an active hold placed by another patron."))
        return redirect("library:user_loans")

    loan.due_date += timedelta(days=duration_days)
    loan.renewal_count += 1
    loan.save()
    messages.success(request, _(f"Loan renewed until {loan.due_date}."))
    return redirect("library:user_loans")


# ==========================================
# Librarian Circulation Desk & CRUD
# ==========================================

@librarian_required
def librarian_dashboard_view(request):
    today = timezone.now().date()
    active_loans = Loan.objects.filter(status=Loan.Status.ACTIVE).select_related("user", "book_copy__book")
    overdue_loans = active_loans.filter(due_date__lt=today)
    unpaid_fines_sum = Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    context = {
        "total_books": Book.objects.count(),
        "available_books": BookCopy.objects.filter(status=BookCopy.Status.AVAILABLE).count(),
        "borrowed_books_count": active_loans.count(),
        "active_loans_count": active_loans.count(),
        "overdue_count": overdue_loans.count(),
        "unpaid_fines_total": unpaid_fines_sum,
        "total_titles": Book.objects.count(),
        "total_copies": BookCopy.objects.count(),
        "recent_loans": active_loans.order_by("-issue_date")[:10],
        "recent_records": active_loans.order_by("-issue_date")[:10],
        "overdue_loans": overdue_loans[:10],
        "issue_form": IssueBookForm(),
    }
    return render(request, "admin_app/dashboard.html", context)


@librarian_required
@require_POST
def issue_book_copy_view(request):
    form = IssueBookForm(request.POST)
    if form.is_valid():
        member_id = form.cleaned_data["member_identifier"].strip()
        barcode = form.cleaned_data["accession_number"].strip()

        user = User.objects.filter(Q(member_id=member_id) | Q(email=member_id)).first()
        if not user:
            messages.error(request, _(f"Borrower '{member_id}' not found."))
            return redirect("library:librarian_dashboard")

        policy = BorrowingPolicy.objects.filter(role=user.role).first()
        max_allowed = policy.max_books if policy else 3
        if Loan.objects.filter(user=user, status=Loan.Status.ACTIVE).count() >= max_allowed:
            messages.error(request, _(f"Checkout blocked: Borrower reached maximum quota of {max_allowed} books."))
            return redirect("library:librarian_dashboard")

        if Fine.objects.filter(loan__user=user, is_paid=False).exists():
            messages.error(request, _("Checkout blocked: Borrower has unpaid fines."))
            return redirect("library:librarian_dashboard")

        with transaction.atomic():
            copy = BookCopy.objects.select_for_update().filter(accession_number=barcode).first()
            if not copy:
                messages.error(request, _(f"Barcode '{barcode}' does not exist."))
                return redirect("library:librarian_dashboard")

            if copy.status != BookCopy.Status.AVAILABLE:
                reserved_for = Reservation.objects.filter(user=user, book=copy.book, is_active=True).first()
                if not (copy.status == BookCopy.Status.RESERVED and reserved_for):
                    messages.error(request, _(f"Copy {barcode} is currently {copy.get_status_display()}."))
                    return redirect("library:librarian_dashboard")

            Reservation.objects.filter(user=user, book=copy.book, is_active=True).update(is_active=False)
            copy.status = BookCopy.Status.ISSUED
            copy.save()
            Loan.objects.create(user=user, book_copy=copy)
            messages.success(request, _(f"Issued '{copy.book.title}' to {user.email}."))
    return redirect("library:librarian_dashboard")


@librarian_required
@require_POST
def return_book_copy_view(request, loan_id):
    with transaction.atomic():
        loan = get_object_or_404(Loan.objects.select_for_update(), pk=loan_id, status=Loan.Status.ACTIVE)
        copy = BookCopy.objects.select_for_update().get(pk=loan.book_copy_id)

        loan.status = Loan.Status.RETURNED
        loan.return_date = timezone.now().date()
        loan.save()

        if loan.overdue_days > 0:
            fine_amount = loan.current_fine
            Fine.objects.create(loan=loan, amount=fine_amount, is_paid=False)
            messages.warning(request, _(f"Returned late. Overdue fine of ₹{fine_amount} assessed."))
        else:
            messages.success(request, _(f"Returned '{copy.book.title}' successfully."))

        pending = Reservation.objects.filter(book=copy.book, is_active=True).order_by("reserved_at").first()
        if pending:
            copy.status = BookCopy.Status.RESERVED
            messages.info(request, _(f"Copy held for waitlisted member {pending.user.email}."))
        else:
            copy.status = BookCopy.Status.AVAILABLE
        copy.save()

    return redirect("library:librarian_dashboard")


@librarian_required
def manage_books_view(request):
    books = Book.objects.select_related("author", "subject").prefetch_related("copies").all()
    book_form = BookForm(prefix="book")
    copy_form = BookCopyForm(prefix="copy")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_book":
            book_form = BookForm(request.POST, request.FILES, prefix="book")
            if book_form.is_valid():
                book_form.save()
                messages.success(request, _("Book title registered in catalog."))
                return redirect("library:manage_books")
        elif action == "create_copy":
            copy_form = BookCopyForm(request.POST, prefix="copy")
            if copy_form.is_valid():
                copy_form.save()
                messages.success(request, _("Physical copy registered with accession barcode."))
                return redirect("library:manage_books")

    return render(
        request,
        "admin_app/book_manage.html",
        {"books": books, "form": book_form, "copy_form": copy_form},
    )


@librarian_required
def book_create_view(request):
    form = BookForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        book = form.save()
        messages.success(request, _(f"Created catalog entry for '{book.title}'."))
        return redirect("library:manage_books")
    return render(request, "admin_app/book_form.html", {"form": form, "title": _("Add New Book")})


@librarian_required
def book_update_view(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = BookForm(request.POST or None, request.FILES or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _(f"Updated '{book.title}'."))
        return redirect("library:manage_books")
    return render(request, "admin_app/book_form.html", {"form": form, "book": book, "title": _("Edit Book")})


@librarian_required
def book_delete_view(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        title = book.title
        book.delete()
        messages.success(request, _(f"Removed '{title}' from catalog."))
        return redirect("library:manage_books")
    return render(request, "admin_app/confirm_delete.html", {"object": book})


@librarian_required
def manage_fines_view(request):
    fines = Fine.objects.select_related("loan__user", "loan__book_copy__book", "cleared_by").order_by(
        "-is_paid", "-created_at"
    )
    return render(request, "admin_app/fine_list.html", {"fines": fines})


@librarian_required
@require_POST
def settle_fine_view(request, fine_id):
    fine = get_object_or_404(Fine, pk=fine_id)
    fine.is_paid = True
    fine.paid_at = timezone.now()
    fine.cleared_by = request.user
    fine.save()
    messages.success(request, _(f"Fine of ₹{fine.amount} cleared."))
    return redirect("library:manage_fines")


@librarian_required
def reports_view(request):
    total_loans = Loan.objects.count()
    overdue_count = Loan.objects.filter(status=Loan.Status.ACTIVE, due_date__lt=timezone.now().date()).count()
    fines_collected = Fine.objects.filter(is_paid=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    fines_pending = Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    popular_books = Book.objects.annotate(loan_count=Count("copies__loans")).order_by("-loan_count")[:5]

    return render(
        request,
        "library/admin/reports.html",
        {
            "total_loans": total_loans,
            "overdue_count": overdue_count,
            "fines_collected": fines_collected,
            "fines_pending": fines_pending,
            "popular_books": popular_books,
        },
    )


@librarian_required
def user_monitor_view(request):
    users = (
        User.objects.annotate(
            active_loans_count=Count("loans", filter=Q(loans__status=Loan.Status.ACTIVE)),
            overdue_loans_count=Count(
                "loans",
                filter=Q(loans__status=Loan.Status.ACTIVE, loans__due_date__lt=timezone.now().date()),
            ),
        )
        .order_by("-active_loans_count")
    )
    return render(request, "library/admin/user_monitor.html", {"monitored_users": users})
