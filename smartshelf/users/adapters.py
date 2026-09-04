from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        user = request.user
        if user.is_authenticated and user.is_librarian:
            return reverse("library:librarian_dashboard")
        return reverse("library:user_loans")


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)