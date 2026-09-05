from django import forms
from .models import Author, Book, Category, Fine


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "isbn", "author", "category", "description", "total_copies", "available_copies", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "isbn": forms.TextInput(attrs={"class": "form-control"}),
            "author": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "total_copies": forms.NumberInput(attrs={"class": "form-control"}),
            "available_copies": forms.NumberInput(attrs={"class": "form-control"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
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


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
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


class IssueBookForm(forms.Form):
    user_email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "User Email"}))
    book_id = forms.IntegerField(widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Book ID"}))
    duration_days = forms.IntegerField(initial=14, widget=forms.NumberInput(attrs={"class": "form-control"}))