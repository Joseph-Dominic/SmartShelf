from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from smartshelf.users.adapters import AccountAdapter
from smartshelf.users.forms import UserAdminChangeForm
from smartshelf.users.models import User
from smartshelf.users.tests.factories import UserFactory
from smartshelf.users.views import UserRedirectView
from smartshelf.users.views import UserUpdateView
from smartshelf.users.views import user_detail_view

if TYPE_CHECKING:
    from django.test import RequestFactory


pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == f"/users/{user.pk}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = user
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == reverse("library:user_loans")


class TestAccountAdapter:
    def test_admin_redirects_to_admin_dashboard(self, rf: RequestFactory):
        request = rf.get("/")
        request.user = UserFactory(is_staff=True)

        assert AccountAdapter().get_login_redirect_url(request) == reverse(
            "admin_app:librarian_dashboard",
        )

    def test_regular_user_redirects_to_loans(self, user: User, rf: RequestFactory):
        request = rf.get("/")
        request.user = user

        expected_url = reverse("library:user_loans")
        assert AccountAdapter().get_login_redirect_url(request) == expected_url


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory.create()
        response = user_detail_view(request, pk=user.pk)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, pk=user.pk)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"


class TestSignupView:
    def test_signup_get_renders_all_fields(self, client):
        response = client.get(reverse("account_signup"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode("utf-8")
        assert 'name="name"' in content
        assert 'name="email"' in content
        assert 'name="role"' in content
        assert 'name="member_id"' in content
        assert 'name="department"' in content
        assert 'name="phone_number"' in content
        assert 'name="password1"' in content
        assert 'name="password2"' in content

    def test_signup_post_success(self, client):
        data = {
            "name": "Integration Student",
            "email": "integration_student@example.com",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-INT",
            "department": "Engineering",
            "phone_number": "1234567890",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        response = client.post(reverse("account_signup"), data)
        assert response.status_code == HTTPStatus.FOUND

        user = User.objects.get(email="integration_student@example.com")
        assert user.name == "Integration Student"
        assert user.role == User.Role.STUDENT_UG
        assert user.member_id == "UG-2026-INT"
        assert user.department == "Engineering"
        assert user.phone_number == "1234567890"

    def test_signup_post_missing_name_fails(self, client):
        data = {
            "name": "",
            "email": "noname_student@example.com",
            "role": User.Role.STUDENT_UG,
            "member_id": "UG-2026-NONAME",
            "department": "Engineering",
            "password1": "SecurePass!2026",
            "password2": "SecurePass!2026",
        }
        response = client.post(reverse("account_signup"), data)
        assert response.status_code == HTTPStatus.OK
        assert not User.objects.filter(email="noname_student@example.com").exists()
        assert "form" in response.context
        assert "name" in response.context["form"].errors

