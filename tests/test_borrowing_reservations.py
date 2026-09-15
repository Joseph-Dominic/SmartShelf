from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from smartshelf.library.models import Author, Book, BookCopy, BorrowingPolicy, Fine, Loan, Reservation, Subject

User = get_user_model()


@pytest.fixture
def ug_policy(db):
    return BorrowingPolicy.objects.create(
        role="STUDENT_UG",
        max_books=3,
        loan_duration_days=14,
        max_renewals=2,
        daily_fine_rate=Decimal("5.00"),
    )


@pytest.fixture
def librarian_user(db):
    return User.objects.create_user(
        email="librarian@test.com",
        password="Password123!",
        role="ADMIN",
        is_staff=True,
        is_superuser=True,
        member_id="LIB-001",
    )


@pytest.fixture
def student_user(db):
    return User.objects.create_user(
        email="student@test.com",
        password="Password123!",
        role="STUDENT_UG",
        member_id="UG-001",
    )


@pytest.fixture
def second_student(db):
    return User.objects.create_user(
        email="student2@test.com",
        password="Password123!",
        role="STUDENT_UG",
        member_id="UG-002",
    )


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Donald Knuth")
    subject = Subject.objects.create(code="CS", name="Computer Science")
    return Book.objects.create(
        title="The Art of Computer Programming",
        isbn="9780201896831",
        author=author,
        subject=subject,
    )


@pytest.mark.django_db
class TestBookReservation:
    def test_get_on_reserve_url_redirects_without_405(self, client, student_user, sample_book):
        client.force_login(student_user)
        url = reverse("library:place_reservation", kwargs={"pk": sample_book.pk})
        response = client.get(url, follow=True)
        assert response.status_code == 200
        # Redirected back to book detail
        assert response.redirect_chain[0][0] == reverse("library:book_detail", kwargs={"pk": sample_book.pk})
        assert Reservation.objects.count() == 0

    def test_reserve_when_copies_available_blocked(self, client, student_user, sample_book):
        BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.AVAILABLE)
        client.force_login(student_user)
        url = reverse("library:place_reservation", kwargs={"pk": sample_book.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        assert Reservation.objects.count() == 0

    def test_reserve_when_no_copies_available_success(self, client, student_user, sample_book):
        BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        client.force_login(student_user)
        url = reverse("library:place_reservation", kwargs={"pk": sample_book.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        assert Reservation.objects.filter(user=student_user, book=sample_book, is_active=True).exists()

    def test_reserve_blocked_if_user_has_active_loan_for_book(self, client, student_user, sample_book):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        Loan.objects.create(user=student_user, book_copy=copy, status=Loan.Status.ACTIVE)
        client.force_login(student_user)
        url = reverse("library:place_reservation", kwargs={"pk": sample_book.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        assert Reservation.objects.count() == 0

    def test_cancel_reservation_via_post(self, client, student_user, sample_book):
        res = Reservation.objects.create(user=student_user, book=sample_book, is_active=True)
        client.force_login(student_user)
        url = reverse("library:cancel_reservation", kwargs={"pk": res.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        res.refresh_from_db()
        assert not res.is_active

    def test_cancel_reservation_reverts_surplus_reserved_copy(self, client, student_user, sample_book):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.RESERVED)
        res = Reservation.objects.create(user=student_user, book=sample_book, is_active=True)
        client.force_login(student_user)
        url = reverse("library:cancel_reservation", kwargs={"pk": res.pk})
        client.post(url, follow=True)
        copy.refresh_from_db()
        assert copy.status == BookCopy.Status.AVAILABLE


@pytest.mark.django_db
class TestBookLoanAndReturn:
    def test_issue_book_success(self, client, librarian_user, student_user, sample_book, ug_policy):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.AVAILABLE)
        client.force_login(librarian_user)
        url = reverse("library:issue_book")
        response = client.post(url, {"member_identifier": "UG-001", "accession_number": "CS-001-A"}, follow=True)
        assert response.status_code == 200
        copy.refresh_from_db()
        assert copy.status == BookCopy.Status.ISSUED
        assert Loan.objects.filter(user=student_user, book_copy=copy, status=Loan.Status.ACTIVE).exists()

    def test_issue_blocked_if_unpaid_fines(self, client, librarian_user, student_user, sample_book, ug_policy):
        copy1 = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.AVAILABLE)
        copy2 = BookCopy.objects.create(book=sample_book, accession_number="CS-001-B", status=BookCopy.Status.AVAILABLE)
        old_loan = Loan.objects.create(user=student_user, book_copy=copy1, status=Loan.Status.RETURNED)
        Fine.objects.create(loan=old_loan, amount=Decimal("25.00"), is_paid=False)

        client.force_login(librarian_user)
        url = reverse("library:issue_book")
        client.post(url, {"member_identifier": "UG-001", "accession_number": "CS-001-B"}, follow=True)
        copy2.refresh_from_db()
        assert copy2.status == BookCopy.Status.AVAILABLE
        assert not Loan.objects.filter(user=student_user, book_copy=copy2).exists()

    def test_return_book_on_time_becomes_available(self, client, librarian_user, student_user, sample_book, ug_policy):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        loan = Loan.objects.create(user=student_user, book_copy=copy, status=Loan.Status.ACTIVE)
        client.force_login(librarian_user)
        url = reverse("library:return_book", kwargs={"loan_id": loan.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        loan.refresh_from_db()
        copy.refresh_from_db()
        assert loan.status == Loan.Status.RETURNED
        assert copy.status == BookCopy.Status.AVAILABLE
        assert not Fine.objects.filter(loan=loan).exists()

    def test_return_book_with_waitlist_becomes_reserved(self, client, librarian_user, student_user, second_student, sample_book, ug_policy):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        loan = Loan.objects.create(user=student_user, book_copy=copy, status=Loan.Status.ACTIVE)
        Reservation.objects.create(user=second_student, book=sample_book, is_active=True)

        client.force_login(librarian_user)
        url = reverse("library:return_book", kwargs={"loan_id": loan.pk})
        client.post(url, follow=True)
        copy.refresh_from_db()
        assert copy.status == BookCopy.Status.RESERVED

    def test_return_book_surplus_copies_not_over_reserved(self, client, librarian_user, student_user, second_student, sample_book, ug_policy):
        # 1 reservation, 2 copies returned: 1 should be RESERVED, the other AVAILABLE
        copy1 = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.RESERVED)
        copy2 = BookCopy.objects.create(book=sample_book, accession_number="CS-001-B", status=BookCopy.Status.ISSUED)
        loan = Loan.objects.create(user=student_user, book_copy=copy2, status=Loan.Status.ACTIVE)
        Reservation.objects.create(user=second_student, book=sample_book, is_active=True)

        client.force_login(librarian_user)
        url = reverse("library:return_book", kwargs={"loan_id": loan.pk})
        client.post(url, follow=True)
        copy2.refresh_from_db()
        assert copy2.status == BookCopy.Status.AVAILABLE


@pytest.mark.django_db
class TestRenewAndFines:
    def test_renew_loan_success(self, client, student_user, sample_book, ug_policy):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        loan = Loan.objects.create(
            user=student_user,
            book_copy=copy,
            status=Loan.Status.ACTIVE,
            due_date=timezone.now().date() + timedelta(days=5),
        )
        initial_due = loan.due_date
        client.force_login(student_user)
        url = reverse("library:renew_loan", kwargs={"pk": loan.pk})
        response = client.post(url, follow=True)
        assert response.status_code == 200
        loan.refresh_from_db()
        assert loan.renewal_count == 1
        assert loan.due_date == initial_due + timedelta(days=14)

    def test_renew_loan_via_get_redirects_safely(self, client, student_user, sample_book, ug_policy):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.ISSUED)
        loan = Loan.objects.create(
            user=student_user,
            book_copy=copy,
            status=Loan.Status.ACTIVE,
            due_date=timezone.now().date() + timedelta(days=5),
        )
        client.force_login(student_user)
        url = reverse("library:renew_loan", kwargs={"pk": loan.pk})
        response = client.get(url, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain[0][0] == reverse("library:user_loans")

    def test_fine_management_view_no_field_error(self, client, librarian_user, student_user, sample_book):
        copy = BookCopy.objects.create(book=sample_book, accession_number="CS-001-A", status=BookCopy.Status.AVAILABLE)
        loan = Loan.objects.create(user=student_user, book_copy=copy, status=Loan.Status.RETURNED)
        Fine.objects.create(loan=loan, amount=Decimal("15.00"), is_paid=False)

        client.force_login(librarian_user)
        url = reverse("library:manage_fines")
        response = client.get(url)
        assert response.status_code == 200
