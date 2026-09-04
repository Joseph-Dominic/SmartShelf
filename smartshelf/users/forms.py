from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": forms.EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        field_classes = {"email": forms.EmailField}
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """Default signup form."""


class UserSocialSignupForm(SocialSignupForm):
    """Default social signup form."""


class CustomUserSignupForm(SignupForm):
    ROLE_CHOICES = (
        (User.Role.STUDENT_UG, "Undergraduate Student (UG)"),
        (User.Role.STUDENT_PG, "Postgraduate Student (PG)"),
        (User.Role.STAFF, "Faculty / College Staff"),
    )

    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True, label="Academic Role")
    member_id = forms.CharField(max_length=30, required=True, label="Roll No / Staff ID")
    department = forms.CharField(max_length=100, required=True, label="Department")
    phone_number = forms.CharField(max_length=15, required=False, label="Phone Number")

    def custom_signup(self, request, user):
        user.role = self.cleaned_data["role"]
        user.member_id = self.cleaned_data["member_id"]
        user.department = self.cleaned_data["department"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.save()
        return user