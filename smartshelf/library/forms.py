from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Author, Book, BookCopy, Subject


class IssueBookForm(forms.Form):
    member_identifier = forms.CharField(
        label=_("Roll No / Staff ID / Email"),
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. UG202401 or student@univ.edu", "autofocus": True}
        ),
    )
    accession_number = forms.CharField(
        label=_("Accession / Barcode Number"),
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CS-001-A"}),
    )


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "isbn", "author", "subject", "edition", "publisher", "description", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "isbn": forms.TextInput(attrs={"class": "form-control"}),
            "author": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "edition": forms.TextInput(attrs={"class": "form-control"}),
            "publisher": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "cover_image": forms.FileInput(attrs={"class": "form-control"}),
        }


class BookCopyForm(forms.ModelForm):
    class Meta:
        model = BookCopy
        fields = ["book", "accession_number", "shelf_location", "status"]
        widgets = {
            "book": forms.Select(attrs={"class": "form-select"}),
            "accession_number": forms.TextInput(attrs={"class": "form-control"}),
            "shelf_location": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["code", "name", "description"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ["name", "biography"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "biography": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }