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