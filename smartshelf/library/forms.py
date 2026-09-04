from django import forms
from .models import Book, BookCopy, Subject, Author


class SubjectForm(forms.ModelForm):
    """Aligns with the academic LMS requirement for Subjects/Departments."""
    class Meta:
        model = Subject
        fields = ["code", "name", "description"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., CS101"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Computer Science"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ["name", "biography"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "biography": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class BookForm(forms.ModelForm):
    """Manages title metadata only. Physical counts are derived from BookCopy."""
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
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class BookCopyForm(forms.ModelForm):
    """Allows librarians to add individual physical copies with shelf tags."""
    class Meta:
        model = BookCopy
        fields = ["book", "accession_number", "shelf_location", "status"]
        widgets = {
            "book": forms.Select(attrs={"class": "form-select"}),
            "accession_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Barcode / Accession ID"}),
            "shelf_location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Shelf B-3"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class IssueBookForm(forms.Form):
    """Fast circulation desk checkout form using unique barcodes and member IDs."""
    member_identifier = forms.CharField(
        label="Student Roll No / Staff ID / Email",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter Roll No, Staff ID, or Email"}),
    )
    accession_number = forms.CharField(
        label="Physical Copy Barcode / Accession No",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Scan or type Barcode ID"}),
    )
    custom_days = forms.IntegerField(
        required=False,
        label="Custom Loan Days (Optional)",
        help_text="Leave empty to apply default role policy duration.",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Default by Role"}),
    )