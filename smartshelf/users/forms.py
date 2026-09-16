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
        fields = ("email",)
        field_classes = {"email": forms.EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    ROLE_CHOICES = (
        (
            User.Role.STUDENT_UG,
            _("Undergraduate Student (UG) — Quota: 3 Books / 14 Days"),
        ),
        (
            User.Role.STUDENT_PG,
            _("Postgraduate Student (PG) — Quota: 5 Books / 21 Days"),
        ),
        (
            User.Role.STAFF,
            _("Faculty / College Staff — Quota: 10 Books / 90 Days"),
        ),
    )

    name = forms.CharField(
        max_length=255,
        required=True,
        label=_("Full Name"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. Alex Johnson"},
        ),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        label=_("Academic Role"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    member_id = forms.CharField(
        max_length=30,
        required=True,
        label=_("Roll No / Employee ID"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. UG-2024-101 or FAC-42",
            },
        ),
    )
    department = forms.CharField(
        max_length=100,
        required=True,
        label=_("Department / Program"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Computer Science",
            },
        ),
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label=_("Phone Number (Optional)"),
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "+91 9876543210"},
        ),
    )

    def clean_email(self):
        email = super().clean_email()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("A user is already registered with this email address."),
            )
        return email

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError(_("Full name is required."))
        return name

    def clean_department(self):
        department = self.cleaned_data.get("department", "").strip()
        if not department:
            raise forms.ValidationError(_("Department is required."))
        return department

    def clean_member_id(self):
        member_id = self.cleaned_data.get("member_id", "").strip().upper()
        if not member_id:
            raise forms.ValidationError(_("Roll No / Employee ID is required."))
        if User.objects.filter(member_id__iexact=member_id).exists():
            raise forms.ValidationError(
                _("This Roll No / Employee ID is already registered."),
            )
        return member_id

    def clean_phone_number(self):
        return self.cleaned_data.get("phone_number", "").strip()

    def signup(self, request, user):
        """Adapter hook called by django-allauth during registration."""
        user.name = self.cleaned_data["name"]
        user.role = self.cleaned_data["role"]
        user.member_id = self.cleaned_data["member_id"]
        user.department = self.cleaned_data["department"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.save()

    def save(self, request):
        """Form save override ensuring attributes persist across allauth versions."""
        user = super().save(request)
        user.name = self.cleaned_data["name"]
        user.role = self.cleaned_data["role"]
        user.member_id = self.cleaned_data["member_id"]
        user.department = self.cleaned_data["department"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.save()
        return user


CustomUserSignupForm = UserSignupForm


class UserSocialSignupForm(SocialSignupForm):
    """Default social signup form."""
