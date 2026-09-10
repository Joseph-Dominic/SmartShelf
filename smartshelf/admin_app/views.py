
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from smartshelf.library.forms import AuthorForm, BookForm, CategoryForm
from smartshelf.library.models import Author, Book, BorrowRecord, Category, Fine

User = get_user_model()


def is_librarian(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def librarian_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not is_librarian(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped_view


@librarian_required
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


@librarian_required
def manage_books(request):
    """Admin book management list."""
    books = Book.objects.select_related("author", "category").all()
    return render(request, "admin_app/book_manage.html", {"books": books})


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
        if request.GET.get("category"):
            initial["category"] = request.GET["category"]
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
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect(f"{reverse('admin_app:book_create')}?category={category.pk}")
    else:
        form = CategoryForm()
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
    categories = Category.objects.all()
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
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect("admin_app:manage_categories")
    else:
        form = CategoryForm(instance=category)
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
    category = get_object_or_404(Category, pk=pk)
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
    """Admin fine collection and status tracking."""
    fines = Fine.objects.select_related("borrow_record__user", "borrow_record__book").order_by("-id")
    return render(request, "admin_app/fine_list.html", {"fines": fines})


@librarian_required
def mark_fine_paid(request, fine_id):
    """Mark a fine as collected/paid."""
    fine = get_object_or_404(Fine, id=fine_id)
    fine.is_paid = True
    fine.paid_at = timezone.now()
    fine.save()
    messages.success(request, f"Fine of ${fine.amount} for {fine.borrow_record.user} marked as paid.")
    return redirect("admin_app:manage_fines")


@librarian_required
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


@librarian_required
def monitor_users(request):
    """Monitor registered users and their loan activities."""
    users = User.objects.annotate(
        total_borrowed=Count("borrow_records"),
        active_loans=Count("borrow_records", filter=Q(borrow_records__status=BorrowRecord.Status.BORROWED)),
    ).order_by("-date_joined")
    return render(request, "admin_app/user_monitor.html", {"monitored_users": users})
