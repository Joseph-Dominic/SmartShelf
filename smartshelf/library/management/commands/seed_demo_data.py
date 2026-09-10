import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from smartshelf.library.models import (
    Subject, Author, Book, BookCopy, BorrowingPolicy, Loan, Fine, Reservation
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with demo users, catalog, and circulation states"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting demo data seeder...")

        # 1. Borrowing Policies
        self.stdout.write("Seeding Borrowing Policies...")
        policies = [
            {"role": "STAFF", "max_books": 10, "loan_duration_days": 90, "max_renewals": 5, "daily_fine_rate": Decimal("0.00")},
            {"role": "STUDENT_PG", "max_books": 5, "loan_duration_days": 21, "max_renewals": 2, "daily_fine_rate": Decimal("5.00")},
            {"role": "STUDENT_UG", "max_books": 3, "loan_duration_days": 14, "max_renewals": 2, "daily_fine_rate": Decimal("5.00")},
        ]
        for p in policies:
            BorrowingPolicy.objects.update_or_create(
                role=p["role"],
                defaults={
                    "max_books": p["max_books"],
                    "loan_duration_days": p["loan_duration_days"],
                    "max_renewals": p["max_renewals"],
                    "daily_fine_rate": p["daily_fine_rate"],
                }
            )

        # 2. Target Existing Accounts
        self.stdout.write("Seeding Users...")
        # Admin
        admin_email = "josephdominic0032@gmail.com"
        admin, _ = User.objects.update_or_create(
            email=admin_email,
            defaults={
                "name": "Admin Librarian",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
                "member_id": "LIB-001",
                "department": "Administration"
            }
        )
        if not admin.has_usable_password():
            admin.set_password("Pass1234#")
            admin.save()

        # UG Student
        ug_student, _ = User.objects.update_or_create(
            email="joseph355576@gmail.com",
            defaults={
                "name": "UG Student",
                "role": "STUDENT_UG",
                "member_id": "UG-2024-01",
                "department": "Computer Science"
            }
        )
        if not ug_student.has_usable_password():
            ug_student.set_password("Pass1234#")
            ug_student.save()

        # PG Student
        pg_student, _ = User.objects.update_or_create(
            email="joseph@gmail.com",
            defaults={
                "name": "PG Student",
                "role": "STUDENT_PG",
                "member_id": "PG-2024-01",
                "department": "Data Science"
            }
        )
        if not pg_student.has_usable_password():
            pg_student.set_password("Pass1234#")
            pg_student.save()

        # Faculty
        faculty, _ = User.objects.update_or_create(
            email="faculty@univ.edu",
            defaults={
                "name": "Faculty Member",
                "role": "STAFF",
                "member_id": "FAC-001",
                "department": "Mechanical Engineering"
            }
        )
        if not faculty.has_usable_password():
            faculty.set_password("Pass1234#")
            faculty.save()

        # 3. Catalog Data
        self.stdout.write("Seeding Catalog Data...")
        # Subjects
        subj_cs, _ = Subject.objects.get_or_create(code="CS", defaults={"name": "Computer Science", "description": "CS Department"})
        subj_me, _ = Subject.objects.get_or_create(code="ME", defaults={"name": "Mechanical Engineering", "description": "ME Department"})
        subj_math, _ = Subject.objects.get_or_create(code="MATH", defaults={"name": "Applied Mathematics", "description": "Math Department"})

        # Authors
        auth1, _ = Author.objects.get_or_create(name="Donald Knuth")
        auth2, _ = Author.objects.get_or_create(name="Alan Turing")
        auth3, _ = Author.objects.get_or_create(name="Isaac Newton")

        # Books
        book1, _ = Book.objects.get_or_create(isbn="978-0131103627", defaults={"title": "The C Programming Language", "author": auth1, "subject": subj_cs})
        book2, _ = Book.objects.get_or_create(isbn="978-0201896831", defaults={"title": "The Art of Computer Programming", "author": auth1, "subject": subj_cs})
        book3, _ = Book.objects.get_or_create(isbn="978-0262033848", defaults={"title": "Introduction to Algorithms", "author": auth2, "subject": subj_cs})
        book4, _ = Book.objects.get_or_create(isbn="978-1234567890", defaults={"title": "Thermodynamics", "author": auth3, "subject": subj_me})
        book5, _ = Book.objects.get_or_create(isbn="978-0987654321", defaults={"title": "Calculus", "author": auth3, "subject": subj_math})

        # Copies
        self.stdout.write("Seeding Physical Copies...")
        b1_c1, _ = BookCopy.objects.get_or_create(accession_number="CS-101-01", defaults={"book": book1, "shelf_location": "A1"})
        b1_c2, _ = BookCopy.objects.get_or_create(accession_number="CS-101-02", defaults={"book": book1, "shelf_location": "A1"})
        
        b2_c1, _ = BookCopy.objects.get_or_create(accession_number="CS-201-01", defaults={"book": book2, "shelf_location": "A2"})
        b2_c2, _ = BookCopy.objects.get_or_create(accession_number="CS-201-02", defaults={"book": book2, "shelf_location": "A2"})
        
        b3_c1, _ = BookCopy.objects.get_or_create(accession_number="CS-301-01", defaults={"book": book3, "shelf_location": "B1"})
        
        # 4. Circulation Scenarios
        self.stdout.write("Seeding Circulation States...")
        today = timezone.now().date()

        # Active Loan (UG Student, Book 1)
        if not Loan.objects.filter(book_copy=b1_c1, status="ACTIVE").exists():
            Loan.objects.create(
                user=ug_student,
                book_copy=b1_c1,
                issue_date=today,
                due_date=today + timedelta(days=14),
                status="ACTIVE"
            )
            b1_c1.status = "ISSUED"
            b1_c1.save()

        # Overdue Loan with Fines (PG Student, Book 2)
        if not Loan.objects.filter(book_copy=b2_c1, status="ACTIVE").exists():
            overdue_issue = today - timedelta(days=30)
            overdue_due = today - timedelta(days=9)
            overdue_loan = Loan.objects.create(
                user=pg_student,
                book_copy=b2_c1,
                issue_date=overdue_issue,
                due_date=overdue_due,
                status="ACTIVE"
            )
            b2_c1.status = "ISSUED"
            b2_c1.save()

        # Active Reservation (UG Student, Book 3)
        b3_c1.status = "ISSUED" # Mark all copies as issued
        b3_c1.save()
        if not Reservation.objects.filter(user=ug_student, book=book3, is_active=True).exists():
            Reservation.objects.create(
                user=ug_student,
                book=book3,
                is_active=True
            )

        self.stdout.write(self.style.SUCCESS("Demo data successfully seeded!"))
