
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from smartshelf.library import views as library_views
from smartshelf.library.forms import AuthorForm
from smartshelf.library.forms import BookForm
from smartshelf.library.forms import SubjectForm
from smartshelf.library.models import Author
from smartshelf.library.models import Book
from smartshelf.library.models import BookCopy
from smartshelf.library.models import Fine
from smartshelf.library.models import Loan
from smartshelf.library.models import Subject

User = get_user_model()


def is_librarian(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def librarian_required(view):
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not is_librarian(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped_view


@librarian_required
def librarian_dashboard(request):
    return library_views.librarian_dashboard_view(request)


@librarian_required
def manage_books(request):
    return library_views.manage_books_view(request)


@librarian_required
def book_create(request):
    """Add a new book to the catalog."""
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f"Book '{book.title}' created successfully.")
            return redirect("admin_app:manage_books")
    else:
        initial = {}
        if request.GET.get("author"):
            initial["author"] = request.GET["author"]
        if request.GET.get("subject"):
            initial["subject"] = request.GET["subject"]
        form = BookForm(initial=initial)
    return render(request, "admin_app/book_form.html", {"form": form, "title": "Add New Book"})


@librarian_required
def author_create(request):
    """Add an author while preparing a new book."""
    if request.method == "POST":
        form = AuthorForm(request.POST)
        if form.is_valid():
            author = form.save()
            messages.success(request, f"Author '{author.name}' created successfully.")
            return redirect(f"{reverse('admin_app:book_create')}?author={author.pk}")
    else:
        form = AuthorForm()
    return render(request, "admin_app/related_object_form.html", {"form": form, "title": "Add Author"})


@librarian_required
def category_create(request):
    """Add a category while preparing a new book."""
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect(f"{reverse('admin_app:book_create')}?subject={category.pk}")
    else:
        form = SubjectForm()
    return render(request, "admin_app/related_object_form.html", {"form": form, "title": "Add Category"})


@librarian_required
def manage_authors(request):
    authors = Author.objects.all()
    return render(request, "admin_app/related_object_manage.html", {
        "objects": authors,
        "object_type": "Authors",
        "singular_type": "Author",
        "add_url": "admin_app:author_create",
        "update_url": "admin_app:author_update",
        "delete_url": "admin_app:author_delete",
    })


@librarian_required
def manage_categories(request):
    categories = Subject.objects.all()
    return render(request, "admin_app/related_object_manage.html", {
        "objects": categories,
        "object_type": "Categories",
        "singular_type": "Category",
        "add_url": "admin_app:category_create",
        "update_url": "admin_app:category_update",
        "delete_url": "admin_app:category_delete",
    })


@librarian_required
def author_update(request, pk):
    author = get_object_or_404(Author, pk=pk)
    if request.method == "POST":
        form = AuthorForm(request.POST, instance=author)
        if form.is_valid():
            form.save()
            messages.success(request, f"Author '{author.name}' updated.")
            return redirect("admin_app:manage_authors")
    else:
        form = AuthorForm(instance=author)
    return render(request, "admin_app/related_object_form.html", {"form": form, "title": f"Edit {author.name}"})


@librarian_required
def category_update(request, pk):
    category = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect("admin_app:manage_categories")
    else:
        form = SubjectForm(instance=category)
    return render(request, "admin_app/related_object_form.html", {"form": form, "title": f"Edit {category.name}"})


@librarian_required
def author_delete(request, pk):
    author = get_object_or_404(Author, pk=pk)
    if request.method == "POST":
        if author.books.exists():
            messages.error(request, "This author cannot be deleted while books still use it.")
            return redirect("admin_app:manage_authors")
        author.delete()
        messages.success(request, "Author deleted.")
        return redirect("admin_app:manage_authors")
    return render(request, "admin_app/related_object_confirm_delete.html", {
        "object": author,
        "object_type": "Author",
        "warning": "This author can only be deleted after all books using it are reassigned or deleted.",
        "cancel_url": "admin_app:manage_authors",
        "delete_url": "admin_app:author_delete",
    })


@librarian_required
def category_delete(request, pk):
    category = get_object_or_404(Subject, pk=pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted.")
        return redirect("admin_app:manage_categories")
    return render(request, "admin_app/related_object_confirm_delete.html", {
        "object": category,
        "object_type": "Category",
        "warning": "Books using this category will remain in the catalog without a category.",
        "cancel_url": "admin_app:manage_categories",
        "delete_url": "admin_app:category_delete",
    })


@librarian_required
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


@librarian_required
def book_delete(request, pk):
    """Delete a book."""
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        book.delete()
        messages.success(request, "Book deleted.")
        return redirect("admin_app:manage_books")
    return render(request, "admin_app/confirm_delete.html", {"object": book})


@librarian_required
def manage_fines(request):
    return library_views.manage_fines_view(request)


@librarian_required
def mark_fine_paid(request, fine_id):
    return library_views.settle_fine_view(request, fine_id)


@librarian_required
def reports_view(request):
    """Generate daily, weekly, and monthly borrowing reports."""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    daily_loans = Loan.objects.filter(issue_date=today).count()
    weekly_loans = Loan.objects.filter(issue_date__gte=week_ago).count()
    monthly_loans = Loan.objects.filter(issue_date__gte=month_ago).count()

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


@librarian_required
def monitor_users(request):
    """Monitor registered users and their loan activities."""
    users = User.objects.annotate(
        total_borrowed=Count("loans"),
        active_loans=Count("loans", filter=Q(loans__status=Loan.Status.ACTIVE)),
    ).order_by("-date_joined")
    return render(request, "admin_app/user_monitor.html", {"monitored_users": users})


def get_next_accession_number(book: Book) -> str:
    """Generate the next unique accession/barcode number for a book."""
    prefix = f"{book.isbn}-C"
    existing_copies = BookCopy.objects.filter(accession_number__startswith=prefix)
    max_num = 0
    for copy in existing_copies:
        suffix = copy.accession_number[len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    if max_num > 0:
        candidate = f"{prefix}{max_num + 1}"
    else:
        candidate = f"{prefix}{book.copies.count() + 1}"

    counter = 1
    while BookCopy.objects.filter(accession_number=candidate).exists():
        counter += 1
        candidate = f"{prefix}{counter}"
    return candidate


@librarian_required
def book_stock_manage(request, pk):
    """View and manage physical stock (copies) for a specific book."""
    book = get_object_or_404(
        Book.objects.select_related("author", "subject").prefetch_related("copies"),
        pk=pk,
    )
    copies = list(book.copies.all().order_by("accession_number"))

    active_loans_qs = Loan.objects.filter(
        book_copy__book=book,
        status=Loan.Status.ACTIVE,
    ).select_related("user")
    active_loans_by_copy = {loan.book_copy_id: loan for loan in active_loans_qs}

    for copy in copies:
        copy.active_loan = active_loans_by_copy.get(copy.id)

    total_copies = len(copies)
    available_copies = sum(
        1 for c in copies if c.status == BookCopy.Status.AVAILABLE
    )
    issued_copies = sum(1 for c in copies if c.status == BookCopy.Status.ISSUED)
    maintenance_copies = sum(
        1 for c in copies if c.status == BookCopy.Status.MAINTENANCE
    )
    lost_copies = sum(1 for c in copies if c.status == BookCopy.Status.LOST)

    suggested_accession = get_next_accession_number(book)

    return render(
        request,
        "admin_app/book_stock.html",
        {
            "book": book,
            "copies": copies,
            "total_copies": total_copies,
            "available_copies": available_copies,
            "issued_copies": issued_copies,
            "maintenance_copies": maintenance_copies,
            "lost_copies": lost_copies,
            "suggested_accession": suggested_accession,
            "status_choices": BookCopy.Status.choices,
        },
    )


@librarian_required
@require_POST
def book_stock_add(request, pk):
    """Add physical copies to increase book stock."""
    book = get_object_or_404(Book, pk=pk)
    mode = request.POST.get("mode", "single")
    shelf_location = request.POST.get("shelf_location", "").strip()

    if mode == "bulk":
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1
        quantity = max(1, min(quantity, 50))

        created_barcodes = []
        for _ in range(quantity):
            barcode = get_next_accession_number(book)
            BookCopy.objects.create(
                book=book,
                accession_number=barcode,
                shelf_location=shelf_location,
                status=BookCopy.Status.AVAILABLE,
            )
            created_barcodes.append(barcode)

        messages.success(
            request,
            f"Successfully added {quantity} new copies to '{book.title}'.",
        )
    else:
        accession_number = request.POST.get("accession_number", "").strip()
        status = request.POST.get("status", BookCopy.Status.AVAILABLE)
        if not accession_number:
            accession_number = get_next_accession_number(book)

        if BookCopy.objects.filter(accession_number=accession_number).exists():
            messages.error(
                request,
                f"A physical copy with barcode '{accession_number}' already exists.",
            )
            return redirect("admin_app:book_stock", pk=book.pk)

        valid_statuses = [choice[0] for choice in BookCopy.Status.choices]
        if status not in valid_statuses:
            status = BookCopy.Status.AVAILABLE

        copy = BookCopy.objects.create(
            book=book,
            accession_number=accession_number,
            shelf_location=shelf_location,
            status=status,
        )
        msg = f"Physical copy '{copy.accession_number}' added to '{book.title}'."
        messages.success(request, msg)

    return redirect("admin_app:book_stock", pk=book.pk)


@librarian_required
@require_POST
def book_copy_update(request, pk):
    """Update status, shelf location, or barcode of an individual copy."""
    copy = get_object_or_404(BookCopy.objects.select_related("book"), pk=pk)
    book = copy.book

    new_accession = request.POST.get("accession_number", "").strip()
    new_shelf_location = request.POST.get("shelf_location", "").strip()
    new_status = request.POST.get("status")

    if new_accession and new_accession != copy.accession_number:
        barcode_in_use = (
            BookCopy.objects.filter(accession_number=new_accession)
            .exclude(pk=copy.pk)
            .exists()
        )
        if barcode_in_use:
            messages.error(
                request, f"Barcode '{new_accession}' is already in use.",
            )
            return redirect("admin_app:book_stock", pk=book.pk)
        copy.accession_number = new_accession

    copy.shelf_location = new_shelf_location

    has_active_loan = copy.loans.filter(status=Loan.Status.ACTIVE).exists()
    valid_statuses = dict(BookCopy.Status.choices)

    if new_status in valid_statuses:
        if has_active_loan and new_status != BookCopy.Status.ISSUED:
            messages.warning(
                request,
                f"Copy '{copy.accession_number}' is currently borrowed. "
                "Return must be completed at circulation desk before changing status.",
            )
        elif not has_active_loan and new_status == BookCopy.Status.ISSUED:
            messages.warning(
                request,
                "Copies cannot be marked as 'Issued' manually; "
                "use circulation desk to loan to a borrower.",
            )
        else:
            copy.status = new_status

    copy.save()
    messages.success(
        request, f"Copy '{copy.accession_number}' updated successfully.",
    )
    return redirect("admin_app:book_stock", pk=book.pk)


@librarian_required
@require_POST
def book_copy_delete(request, pk):
    """Delete an unissued physical copy to decrease book stock."""
    copy = get_object_or_404(BookCopy.objects.select_related("book"), pk=pk)
    book_pk = copy.book.pk
    barcode = copy.accession_number

    is_borrowed = (
        copy.status == BookCopy.Status.ISSUED
        or copy.loans.filter(status=Loan.Status.ACTIVE).exists()
    )
    if is_borrowed:
        messages.error(
            request,
            f"Cannot delete copy '{barcode}' because it is currently on active loan.",
        )
        return redirect("admin_app:book_stock", pk=book_pk)

    copy.delete()
    messages.success(
        request, f"Physical copy '{barcode}' deleted. Stock decreased.",
    )
    return redirect("admin_app:book_stock", pk=book_pk)

