from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import BookForm
from .models import Author
from .models import Book
from .models import Category

User = get_user_model()


class BookFormTests(TestCase):
    def setUp(self):
        self.author = Author.objects.create(name="Octavia Butler")

    def book_data(self, **overrides):
        data = {
            "title": "Kindred",
            "isbn": "9780807083697",
            "author": self.author.pk,
            "description": "A novel.",
            "total_copies": 3,
            "available_copies": 3,
        }
        data.update(overrides)
        return data

    def test_available_copies_cannot_exceed_total_copies(self):
        form = BookForm(data=self.book_data(available_copies=4))

        assert not form.is_valid()
        assert "available_copies" in form.errors

    def test_edit_cannot_remove_borrowed_copies(self):
        book_data = self.book_data(total_copies=3, available_copies=2)
        book_data["author"] = self.author
        book = Book.objects.create(
            **book_data,
        )
        form = BookForm(
            instance=book,
            data=self.book_data(total_copies=0, available_copies=0),
        )

        assert not form.is_valid()
        assert "total_copies" in form.errors


class AdminBookCrudTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="librarian@example.com",
            password=None,
            is_staff=True,
        )
        self.author = Author.objects.create(name="Ursula Le Guin")
        self.category = Category.objects.create(name="Science Fiction")
        self.client.force_login(self.admin)

    def book_data(self, **overrides):
        data = {
            "title": "The Dispossessed",
            "isbn": "9780061054884",
            "author": self.author.pk,
            "category": self.category.pk,
            "description": "A science-fiction novel.",
            "total_copies": 2,
            "available_copies": 2,
        }
        data.update(overrides)
        return data

    def test_staff_can_create_update_and_delete_book(self):
        create_response = self.client.post(
            reverse("admin_app:book_create"),
            self.book_data(),
        )
        self.assertRedirects(create_response, reverse("admin_app:manage_books"))
        book = Book.objects.get(isbn="9780061054884")
        assert book.title == "The Dispossessed"

        update_response = self.client.post(
            reverse("admin_app:book_update", args=[book.pk]),
            self.book_data(title="The Left Hand of Darkness", isbn=book.isbn),
        )
        self.assertRedirects(update_response, reverse("admin_app:manage_books"))
        book.refresh_from_db()
        assert book.title == "The Left Hand of Darkness"

        delete_response = self.client.post(
            reverse("admin_app:book_delete", args=[book.pk]),
        )
        self.assertRedirects(delete_response, reverse("admin_app:manage_books"))
        assert not Book.objects.filter(pk=book.pk).exists()

    def test_non_staff_cannot_access_book_management(self):
        self.client.logout()
        user = User.objects.create_user(
            email="member@example.com",
            password=None,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_app:manage_books"))

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_staff_can_create_author_and_category_from_admin_flow(self):
        author_response = self.client.post(
            reverse("admin_app:author_create"),
            {"name": "James Baldwin", "biography": "A novelist."},
        )
        self.assertRedirects(
            author_response,
            f"{reverse('admin_app:book_create')}?author={Author.objects.get(name='James Baldwin').pk}",
        )

        category_response = self.client.post(
            reverse("admin_app:category_create"),
            {"name": "Literary Fiction", "description": "Fiction."},
        )
        self.assertRedirects(
            category_response,
            f"{reverse('admin_app:book_create')}?category={Category.objects.get(name='Literary Fiction').pk}",
        )

    def test_staff_can_edit_authors_and_categories(self):
        author_response = self.client.post(
            reverse("admin_app:author_update", args=[self.author.pk]),
            {"name": "Ursula K. Le Guin", "biography": "Updated biography."},
        )
        self.assertRedirects(author_response, reverse("admin_app:manage_authors"))
        self.author.refresh_from_db()
        assert self.author.name == "Ursula K. Le Guin"

        category_response = self.client.post(
            reverse("admin_app:category_update", args=[self.category.pk]),
            {"name": "Speculative Fiction", "description": "Updated description."},
        )
        self.assertRedirects(category_response, reverse("admin_app:manage_categories"))
        self.category.refresh_from_db()
        assert self.category.name == "Speculative Fiction"

    def test_staff_can_view_author_and_category_management_pages(self):
        author_response = self.client.get(reverse("admin_app:manage_authors"))
        category_response = self.client.get(reverse("admin_app:manage_categories"))

        assert author_response.status_code == HTTPStatus.OK
        assert category_response.status_code == HTTPStatus.OK
        assert "Ursula Le Guin" in author_response.content.decode()
        assert "Science Fiction" in category_response.content.decode()

    def test_staff_can_delete_category(self):
        response = self.client.post(reverse("admin_app:category_delete", args=[self.category.pk]))

        self.assertRedirects(response, reverse("admin_app:manage_categories"))
        assert not Category.objects.filter(pk=self.category.pk).exists()

    def test_author_with_books_cannot_be_deleted(self):
        Book.objects.create(
            title="The Left Hand of Darkness",
            isbn="9780441478125",
            author=self.author,
            category=self.category,
            total_copies=1,
            available_copies=1,
        )

        response = self.client.post(reverse("admin_app:author_delete", args=[self.author.pk]))

        self.assertRedirects(response, reverse("admin_app:manage_authors"))
        assert Author.objects.filter(pk=self.author.pk).exists()


# Create your tests here.
