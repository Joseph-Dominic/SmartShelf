from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .forms import BookCopyForm, BookForm, IssueBookForm
from .models import Book, BookCopy, BorrowingPolicy, Fine, Loan, Reservation, Subject

User = get_user_model()


def librarian_required(view_func):
    """Decorator ensuring only staff or librarian accounts access circulation desk views."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("account_login")
        if not getattr(request.user, "is_librarian", False):
            raise PermissionDenied(_("Access restricted to library administrators."))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==========================================
# Public Catalog & Holds
# ==========================================

def book_list_view(request):
    query = request.GET.get("q", "").strip()
    subject_id = request.GET.get("subject", "").strip()

    books = Book.objects.select_related("author", "subject").prefetch_related("copies").all()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(author__name__icontains=query)
        )
    if subject_id:
        books = books.filter(subject_id=subject_id)

    subjects = Subject.objects.all()
    context = {
        "books": books,
        "subjects": subjects,
        "query": query,
        "selected_subject": subject_id,
    }
    return render(request, "library/book_list.html", context)


def book_detail_view(request, pk):
    book = get_object_or_404(Book.objects.select_related("author", "subject").prefetch_related("copies"), pk=pk)
    has_active_reservation = False
    if request.user.is_authenticated:
        has_active_reservation = Reservation.objects.filter(user=request.user, book=book, is_active=True).exists()

    context = {
        "book": book,
        "has_active_reservation": has_active_reservation,
    }
    return render(request, "library/book_detail.html", context)


@login_required
def place_reservation_view(request, pk):
    book = get_object_or_404(Book, pk=pk)

    if book.available_copies > 0:
        messages.warning(request, _("Copies are currently available on the shelf. You do not need a hold."))
        return redirect("library:book_detail", pk=pk)

    reservation, created = Reservation.objects.get_or_create(
        user=request.user,
        book=book,
        is_active=True,
    )
    if created:
        messages.success(request, _("Hold successfully placed. You will be notified when a copy is returned."))
    else:
        messages.info(request, _("You already have an active hold on this title."))
    return redirect("library:book_detail", pk=pk)


@login_required
def cancel_reservation_view(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, user=request.user, is_active=True)
    reservation.is_active = False
    reservation.save()
    messages.success(request, _("Hold reservation canceled."))
    return redirect("library:user_loans")


# ==========================================
# Borrower Portal & Self-Renewals
# ==========================================

@login_required
def user_loans_view(request):
    loans = Loan.objects.filter(user=request.user).select_related("book_copy__book", "book_copy__book__author").order_by("-issue_date")
    reservations = Reservation.objects.filter(user=request.user, is_active=True).select_related("book")
    unpaid_fines = Fine.objects.filter(loan__user=request.user, is_paid=False).select_related("loan__book_copy__book")

    context = {
        "loans": loans,
        "reservations": reservations,
        "unpaid_fines": unpaid_fines,
    }
    return render(request, "library/user_loans.html", context)


@login_required
def renew_loan_view(request, pk):
    loan = get_object_or_404(Loan, pk=pk, user=request.user, status=Loan.Status.ACTIVE)
    policy = BorrowingPolicy.objects.filter(role=request.user.role).first()
    max_renewals = policy.max_renewals if policy else 2
    duration_days = policy.loan_duration_days if policy else 14

    # Rule 1: Cannot renew if overdue
    if loan.due_date < timezone.now().date():
        messages.error(request, _("Cannot renew: this loan is overdue. Please return the book to the circulation desk."))
        return redirect("library:user_loans")

    # Rule 2: Renewal cap
    if loan.renewal_count >= max_renewals:
        messages.error(request, _(f"Maximum renewal allowance ({max_renewals}) reached for this item."))
        return redirect("library:user_loans")

    # Rule 3: Unpaid fines block renewal
    has_unpaid_fines = Fine.objects.filter(loan__user=request.user, is_paid=False).exists()
    if has_unpaid_fines:
        messages.error(request, _("Cannot renew: please clear outstanding fines before requesting extensions."))
        return redirect("library:user_loans")

    # Rule 4: Active hold check by another member
    hold_exists = Reservation.objects.filter(
        book=loan.book_copy.book, is_active=True
    ).exclude(user=request.user).exists()
    if hold_exists:
        messages.error(request, _("Cannot renew: another borrower has placed a hold on this book."))
        return redirect("library:user_loans")

    # Apply extension
    loan.due_date += timedelta(days=duration_days)
    loan.renewal_count += 1
    loan.save()
    messages.success(request, _(f"Successfully renewed. New due date: {loan.due_date}"))
    return redirect("library:user_loans")


# ==========================================
# Librarian Circulation Desk
# ==========================================

@librarian_required
def librarian_dashboard_view(request):
    today = timezone.now().date()
    active_loans = Loan.objects.filter(status=Loan.Status.ACTIVE).select_related("user", "book_copy__book")
    overdue_loans = active_loans.filter(due_date__lt=today)
    unpaid_fines_sum = Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    context = {
        "active_loans_count": active_loans.count(),
        "overdue_count": overdue_loans.count(),
        "unpaid_fines_total": unpaid_fines_sum,
        "total_titles": Book.objects.count(),
        "total_copies": BookCopy.objects.count(),
        "recent_loans": active_loans.order_by("-issue_date")[:10],
        "overdue_loans": overdue_loans[:10],
    }
    return render(request, "library/admin/dashboard.html", context)


@librarian_required
def issue_book_copy_view(request):
    if request.method == "POST":
        form = IssueBookForm(request.POST)
        if form.is_valid():
            member_id = form.cleaned_data["member_identifier"].strip()
            barcode = form.cleaned_data["accession_number"].strip()

            user = User.objects.filter(Q(member_id=member_id) | Q(email=member_id)).first()
            if not user:
                messages.error(request, _(f"Borrower '{member_id}' not found."))
                return render(request, "library/admin/dashboard.html", {"issue_form": form})

            # Check borrowing policy limits
            policy = BorrowingPolicy.objects.filter(role=user.role).first()
            max_allowed = policy.max_books if policy else 3
            current_active_loans = Loan.objects.filter(user=user, status=Loan.Status.ACTIVE).count()

            if current_active_loans >= max_allowed:
                messages.error(request, _(f"Borrower quota exceeded. Maximum allowed: {max_allowed} books."))
                return redirect("library:librarian_dashboard")

            # Check unpaid fine block
            if Fine.objects.filter(loan__user=user, is_paid=False).exists():
                messages.error(request, _("Borrower has unsettled fines. Clear balance before checkout."))
                return redirect("library:librarian_dashboard")

            with transaction.atomic():
                copy = BookCopy.objects.select_for_update().filter(accession_number=barcode).first()
                if not copy:
                    messages.error(request, _(f"Physical copy with barcode '{barcode}' does not exist."))
                    return redirect("library:librarian_dashboard")

                if copy.status != BookCopy.Status.AVAILABLE:
                    # Check if copy was reserved specifically for this member
                    reserved_for_user = Reservation.objects.filter(user=user, book=copy.book, is_active=True).first()
                    if not (copy.status == BookCopy.Status.RESERVED and reserved_for_user):
                        messages.error(request, _(f"Copy {barcode} is currently marked as '{copy.get_status_display()}'. Cannot checkout."))
                        return redirect("library:librarian_dashboard")

                # Deactivate hold if borrower picked it up
                Reservation.objects.filter(user=user, book=copy.book, is_active=True).update(is_active=False)

                copy.status = BookCopy.Status.ISSUED
                copy.save()

                Loan.objects.create(user=user, book_copy=copy)
                messages.success(request, _(f"Successfully issued '{copy.book.title}' ({copy.accession_number}) to {user.email}."))
                return redirect("library:librarian_dashboard")
    return redirect("library:librarian_dashboard")


@librarian_required
def return_book_copy_view(request, loan_id):
    with transaction.atomic():
        loan = get_object_or_404(Loan.objects.select_for_update(), pk=loan_id, status=Loan.Status.ACTIVE)
        copy = BookCopy.objects.select_for_update().get(pk=loan.book_copy_id)

        today = timezone.now().date()
        loan.status = Loan.Status.RETURNED
        loan.return_date = today
        loan.save()

        # Overdue fine settlement creation
        if loan.overdue_days > 0:
            fine_amount = loan.current_fine
            Fine.objects.create(loan=loan, amount=fine_amount, is_paid=False)
            messages.warning(request, _(f"Book returned past due. Overdue fee of ₹{fine_amount} recorded."))
        else:
            messages.success(request, _(f"Returned '{copy.book.title}' successfully."))

        # Reassign to hold queue or return to shelf
        pending_reservation = Reservation.objects.filter(book=copy.book, is_active=True).order_by("reserved_at").first()
        if pending_reservation:
            copy.status = BookCopy.Status.RESERVED
            messages.info(request, _(f"Copy placed on HOLD for borrower {pending_reservation.user.email}."))
        else:
            copy.status = BookCopy.Status.AVAILABLE
        copy.save()

    return redirect("library:librarian_dashboard")


@librarian_required
def manage_books_view(request):
    books = Book.objects.select_related("author", "subject").prefetch_related("copies").all()
    form = BookForm()
    copy_form = BookCopyForm()
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _("Book title added to catalog."))
            return redirect("library:manage_books")
    return render(request, "library/admin/book_manage.html", {"books": books, "form": form, "copy_form": copy_form})


@librarian_required
def manage_fines_view(request):
    fines = Fine.objects.select_related("loan__user", "loan__book_copy__book", "cleared_by").order_by("-is_paid", "-loan__issue_date")
    return render(request, "library/admin/fine_list.html", {"fines": fines})


@librarian_required
def settle_fine_view(request, fine_id):
    fine = get_object_or_404(Fine, pk=fine_id)
    fine.is_paid = True
    fine.paid_at = timezone.now()
    fine.cleared_by = request.user
    fine.save()
    messages.success(request, _(f"Fine of ₹{fine.amount} for {fine.loan.user.email} marked as cleared."))
    return redirect("library:manage_fines")