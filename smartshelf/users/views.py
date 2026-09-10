from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from smartshelf.library.models import BorrowingPolicy, Loan
from smartshelf.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "pk"
    slug_url_kwarg = "pk"
    context_object_name = "user_obj"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_user = self.object
        active_loans = Loan.objects.filter(user=target_user, status=Loan.Status.ACTIVE)
        today = timezone.now().date()

        context["policy"] = BorrowingPolicy.objects.filter(role=target_user.role).first()
        context["active_loans_count"] = active_loans.count()
        context["has_overdue"] = active_loans.filter(due_date__lt=today).exists()
        return context


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name", "phone_number", "department"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        if self.request.user.is_librarian:
            return reverse("library:librarian_dashboard")
        return reverse("library:user_loans")


user_redirect_view = UserRedirectView.as_view()