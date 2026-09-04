# smartshelf/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Librarian / Admin"
        STAFF = "STAFF", "Faculty / Staff"
        STUDENT_PG = "STUDENT_PG", "Postgraduate (PG)"
        STUDENT_UG = "STUDENT_UG", "Undergraduate (UG)"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT_UG,
        help_text="Designates borrowing quota and renewal permissions."
    )
    member_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Roll number for students or Employee ID for staff."
    )
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)

    @property
    def is_librarian(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_student(self):
        return self.role in [self.Role.STUDENT_UG, self.Role.STUDENT_PG]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"