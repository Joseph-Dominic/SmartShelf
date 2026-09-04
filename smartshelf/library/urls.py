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

    # Librarian / Admin routes
   path("manage/dashboard/", views.librarian_dashboard, name="librarian_dashboard"),
    path("manage/books/", views.manage_books, name="manage_books"),
    path("manage/books/add/", views.book_create, name="book_create"),
    path("manage/books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("manage/books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("manage/fines/", views.manage_fines, name="manage_fines"),
    path("manage/fines/<int:fine_id>/pay/", views.mark_fine_paid, name="mark_fine_paid"),
    path("manage/reports/", views.reports_view, name="reports"),
    path("manage/users/", views.monitor_users, name="monitor_users"),
]
