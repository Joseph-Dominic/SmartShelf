"""Unit tests for stock and physical copies management in admin_app."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse
from django.utils import timezone

from smartshelf.library.models import Author
from smartshelf.library.models import Book
from smartshelf.library.models import BookCopy
from smartshelf.library.models import Loan
from smartshelf.library.models import Subject
from smartshelf.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from smartshelf.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user() -> User:
    return UserFactory.create(is_staff=True, is_superuser=True)


@pytest.fixture
def test_book() -> Book:
    author = Author.objects.create(name="Robert C. Martin")
    subject = Subject.objects.create(code="CS-SE", name="Software Engineering")
    return Book.objects.create(
        title="Clean Architecture",
        isbn="978-0134494166",
        author=author,
        subject=subject,
    )


class TestBookStockManagement:
    """Test suite for managing book stocks and physical copies."""

    def test_receive_book_by_isbn_marks_loan_returned_and_copy_available(
        self, client, admin_user, test_book,
    ):
        client.force_login(admin_user)
        borrower = UserFactory.create()
        copy = BookCopy.objects.create(
            book=test_book,
            accession_number="RECEIVE-01",
            status=BookCopy.Status.ISSUED,
        )
        loan = Loan.objects.create(
            user=borrower,
            book_copy=copy,
            due_date=timezone.now().date() + timezone.timedelta(days=14),
            status=Loan.Status.ACTIVE,
        )

        url = reverse("admin_app:receive_book")
        response = client.post(url, {"isbn": test_book.isbn}, follow=True)

        assert response.status_code == HTTPStatus.OK
        loan.refresh_from_db()
        copy.refresh_from_db()
        assert loan.status == Loan.Status.RETURNED
        assert loan.return_date == timezone.now().date()
        assert copy.status == BookCopy.Status.AVAILABLE

    def test_receive_book_by_isbn_rejects_ambiguous_active_loans(
        self, client, admin_user, test_book,
    ):
        client.force_login(admin_user)
        borrowers = [UserFactory.create(), UserFactory.create()]
        loans = []
        for borrower, accession_number in zip(borrowers, ("RECEIVE-02", "RECEIVE-03")):
            copy = BookCopy.objects.create(
                book=test_book,
                accession_number=accession_number,
                status=BookCopy.Status.ISSUED,
            )
            loans.append(Loan.objects.create(
                user=borrower,
                book_copy=copy,
                due_date=timezone.now().date() + timezone.timedelta(days=14),
                status=Loan.Status.ACTIVE,
            ))

        url = reverse("admin_app:receive_book")
        response = client.post(url, {"isbn": test_book.isbn})

        assert response.status_code == HTTPStatus.OK
        assert borrowers[0].email.encode() in response.content
        assert borrowers[1].email.encode() in response.content
        assert b"RECEIVE-02" in response.content
        assert b"RECEIVE-03" in response.content

        response = client.post(url, {"isbn": test_book.isbn, "loan_id": loans[1].pk}, follow=True)

        assert response.status_code == HTTPStatus.OK
        loans[0].refresh_from_db()
        loans[1].refresh_from_db()
        assert loans[0].status == Loan.Status.ACTIVE
        assert loans[1].status == Loan.Status.RETURNED

    def test_librarian_can_view_stock_page(self, client, admin_user, test_book):
        client.force_login(admin_user)
        BookCopy.objects.create(
            book=test_book,
            accession_number="978-0134494166-C1",
            shelf_location="Stack A-1",
            status=BookCopy.Status.AVAILABLE,
        )

        url = reverse("admin_app:book_stock", kwargs={"pk": test_book.pk})
        response = client.get(url)

        assert response.status_code == HTTPStatus.OK
        content = response.content.decode("utf-8")
        assert "Clean Architecture" in content
        assert "978-0134494166-C1" in content
        assert "Stack A-1" in content
        assert admin_user.email in content
        assert "Jitu Chauhan" not in content
        assert "Borrowing Limits &amp; Profile" not in content

    def test_anonymous_and_student_access_restricted(self, client, test_book):
        url = reverse("admin_app:book_stock", kwargs={"pk": test_book.pk})

        # Anonymous user should redirect to login
        anon_resp = client.get(url)
        assert anon_resp.status_code == HTTPStatus.FOUND

        # Regular student user should be denied with 403 Forbidden
        student = UserFactory.create(is_staff=False, is_superuser=False)
        client.force_login(student)
        student_resp = client.get(url)
        assert student_resp.status_code == HTTPStatus.FORBIDDEN

    def test_add_single_copy(self, client, admin_user, test_book):
        client.force_login(admin_user)
        url = reverse("admin_app:book_stock_add", kwargs={"pk": test_book.pk})

        data = {
            "mode": "single",
            "accession_number": "BARCODE-001",
            "shelf_location": "Row 4, Shelf 2",
            "status": BookCopy.Status.AVAILABLE,
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == HTTPStatus.OK

        copy = BookCopy.objects.filter(accession_number="BARCODE-001").first()
        assert copy is not None
        assert copy.book == test_book
        assert copy.shelf_location == "Row 4, Shelf 2"
        assert copy.status == BookCopy.Status.AVAILABLE
        assert test_book.total_copies == 1
        assert test_book.available_copies == 1

    def test_add_bulk_copies(self, client, admin_user, test_book):
        client.force_login(admin_user)
        url = reverse("admin_app:book_stock_add", kwargs={"pk": test_book.pk})

        expected_count = 3
        data = {
            "mode": "bulk",
            "quantity": expected_count,
            "shelf_location": "Section C",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == HTTPStatus.OK

        assert test_book.copies.count() == expected_count
        for copy in test_book.copies.all():
            assert copy.shelf_location == "Section C"
            assert copy.status == BookCopy.Status.AVAILABLE

    def test_duplicate_barcode_rejected(self, client, admin_user, test_book):
        client.force_login(admin_user)
        BookCopy.objects.create(
            book=test_book,
            accession_number="DUPLICATE-BC",
            status=BookCopy.Status.AVAILABLE,
        )

        url = reverse("admin_app:book_stock_add", kwargs={"pk": test_book.pk})
        response = client.post(
            url,
            {
                "mode": "single",
                "accession_number": "DUPLICATE-BC",
                "shelf_location": "Any",
            },
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        assert test_book.copies.count() == 1

    def test_update_copy_status_and_shelf_location(
        self, client, admin_user, test_book,
    ):
        client.force_login(admin_user)
        copy = BookCopy.objects.create(
            book=test_book,
            accession_number="UPDATE-ME-01",
            shelf_location="Old Shelf",
            status=BookCopy.Status.AVAILABLE,
        )

        url = reverse("admin_app:book_copy_update", kwargs={"pk": copy.pk})
        response = client.post(
            url,
            {
                "accession_number": "UPDATE-ME-01",
                "shelf_location": "New Shelf",
                "status": BookCopy.Status.MAINTENANCE,
            },
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK

        copy.refresh_from_db()
        assert copy.shelf_location == "New Shelf"
        assert copy.status == BookCopy.Status.MAINTENANCE
        assert test_book.available_copies == 0
        assert test_book.total_copies == 1

    def test_delete_unissued_copy_decreases_stock(
        self, client, admin_user, test_book,
    ):
        client.force_login(admin_user)
        copy = BookCopy.objects.create(
            book=test_book,
            accession_number="DELETE-ME-01",
            status=BookCopy.Status.AVAILABLE,
        )
        assert test_book.copies.count() == 1

        url = reverse("admin_app:book_copy_delete", kwargs={"pk": copy.pk})
        response = client.post(url, follow=True)
        assert response.status_code == HTTPStatus.OK

        assert not BookCopy.objects.filter(pk=copy.pk).exists()
        assert test_book.copies.count() == 0

    def test_cannot_delete_borrowed_copy(
        self, client, admin_user, test_book,
    ):
        client.force_login(admin_user)
        borrower = UserFactory.create()
        copy = BookCopy.objects.create(
            book=test_book,
            accession_number="BORROWED-01",
            status=BookCopy.Status.ISSUED,
        )
        Loan.objects.create(
            user=borrower,
            book_copy=copy,
            due_date=timezone.now().date() + timezone.timedelta(days=14),
            status=Loan.Status.ACTIVE,
        )

        url = reverse("admin_app:book_copy_delete", kwargs={"pk": copy.pk})
        response = client.post(url, follow=True)
        assert response.status_code == HTTPStatus.OK

        # Copy should remain in DB
        assert BookCopy.objects.filter(pk=copy.pk).exists()
