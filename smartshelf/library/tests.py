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


# Create your tests here.
