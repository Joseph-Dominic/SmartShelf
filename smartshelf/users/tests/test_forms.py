"""Module for all Form Tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.translation import gettext_lazy as _

from smartshelf.users.forms import UserAdminCreationForm
from smartshelf.users.forms import UserSignupForm
from smartshelf.users.models import User

if TYPE_CHECKING:
    from django.test import RequestFactory

pytestmark = pytest.mark.django_db


class TestUserAdminCreationForm:
    """Test class for all tests related to the UserAdminCreationForm."""

    def test_username_validation_error_msg(self, user: User):
        """Tests UserAdminCreation Form's unique validator functions correctly."""
        form = UserAdminCreationForm(
            {
                "email": user.email,
                "password1": user.password,
                "password2": user.password,
            },
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "email" in form.errors
        assert form.errors["email"][0] == _("This email has already been taken.")


class TestUserSignupForm:
    """Tests for the public registration / create account form (UserSignupForm)."""

    def test_valid_signup_form(self, rf: RequestFactory):
        data = {
            "email": "newstudent@example.com",
            "name": "  Jane Doe  ",
            "role": User.Role.STUDENT_UG,
            "member_id": "ug-2026-001",
            "department": "  Computer Science  ",
            "phone_number": "  9876543210  ",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert form.is_valid(), form.errors
        assert form.cleaned_data["name"] == "Jane Doe"
        assert form.cleaned_data["member_id"] == "UG-2026-001"
        assert form.cleaned_data["department"] == "Computer Science"
        assert form.cleaned_data["phone_number"] == "9876543210"

        request = rf.post("/accounts/signup/")
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

        created_user = form.save(request)
        assert created_user.pk is not None
        assert created_user.email == "newstudent@example.com"
        assert created_user.name == "Jane Doe"
        assert created_user.role == User.Role.STUDENT_UG
        assert created_user.member_id == "UG-2026-001"
        assert created_user.department == "Computer Science"
        assert created_user.phone_number == "9876543210"

    def test_signup_missing_name(self):
        data = {
            "email": "noname@example.com",
            "name": "   ",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-002",
            "department": "Physics",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "name" in form.errors

    def test_signup_missing_department(self):
        data = {
            "email": "nodep@example.com",
            "name": "John Doe",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-003",
            "department": "  ",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "department" in form.errors

    def test_signup_missing_member_id(self):
        data = {
            "email": "noid@example.com",
            "name": "John Doe",
            "role": User.Role.STUDENT_UG,
            "member_id": "  ",
            "department": "Chemistry",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "member_id" in form.errors

    def test_signup_duplicate_member_id(self):
        User.objects.create_user(
            email="existing_id@example.com",
            password="SecurePassword123!",  # noqa: S106
            name="Existing User",
            member_id="UG-2026-EXISTING",
        )

        data = {
            "email": "different_email@example.com",
            "name": "Second User",
            "role": User.Role.STUDENT_UG,
            "member_id": "ug-2026-existing",  # case-insensitive match
            "department": "Math",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "member_id" in form.errors
        expected_err = _("This Roll No / Employee ID is already registered.")
        assert expected_err in form.errors["member_id"]

    def test_signup_duplicate_email(self, user: User):
        data = {
            "email": user.email,
            "name": "Another User",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-UNIQUE",
            "department": "Biology",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "email" in form.errors

    def test_signup_password_mismatch(self):
        data = {
            "email": "mismatch@example.com",
            "name": "Mismatch User",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-999",
            "department": "History",
            "password1": "SecurePass!2026",
            "password2": "DifferentPass!2026",
        }
        form = UserSignupForm(data)
        assert not form.is_valid()
        assert "password2" in form.errors
