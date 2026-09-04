from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from smartshelf.users.models import User

if TYPE_CHECKING:
    from django.db.models import QuerySet


# smartshelf/users/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from smartshelf.library.models import BorrowingPolicy, Loan
from .models import User

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "users/user_detail.html"
    context_object_name = "user_obj"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Pull active policy
        policy = BorrowingPolicy.objects.filter(role=user.role).first()
        active_loans = Loan.objects.filter(user=user, status="ACTIVE")
        
        context["policy"] = policy
        context["active_loans_count"] = active_loans.count()
        context["has_overdue"] = any(loan.overdue_days > 0 for loan in active_loans)
        return context


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()
