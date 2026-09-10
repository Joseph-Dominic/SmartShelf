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

    def clean(self):
        cleaned_data = super().clean()
        total_copies = cleaned_data.get("total_copies")
        available_copies = cleaned_data.get("available_copies")

        if total_copies is not None and total_copies < 1:
            self.add_error("total_copies", "A book must have at least one copy.")
        if (
            total_copies is not None
            and available_copies is not None
            and available_copies > total_copies
        ):
            self.add_error("available_copies", "Available copies cannot exceed total copies.")

        if self.instance.pk and total_copies is not None:
            borrowed_copies = self.instance.total_copies - self.instance.available_copies
            if total_copies < borrowed_copies:
                self.add_error(
                    "total_copies",
                    f"Total copies cannot be less than the {borrowed_copies} currently borrowed.",
                )
        return cleaned_data


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