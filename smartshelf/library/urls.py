from django.urls import path

from . import views

app_name = "library"

urlpatterns = [
    # User / Borrower routes
    path("", views.book_catalog, name="book_list"),
    path("book/<int:pk>/", views.book_detail, name="book_detail"),
    path("book/<int:pk>/borrow/", views.borrow_book, name="borrow_book"),
    path("return/<int:record_id>/", views.return_book, name="return_book"),
    path("my-loans/", views.user_loans, name="user_loans"),
]