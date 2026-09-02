from django.urls import path

from smartshelf.admin_app import views as admin_views

from . import views

app_name = "library"

urlpatterns = [
    # User / Borrower routes
    path("", views.book_catalog, name="book_list"),
    path("book/<int:pk>/", views.book_detail, name="book_detail"),
    path("book/<int:pk>/borrow/", views.borrow_book, name="borrow_book"),
    path("return/<int:record_id>/", views.return_book, name="return_book"),
    path("my-loans/", views.user_loans, name="user_loans"),

    # Backward-compatible admin routes for existing templates and links
    path("manage/dashboard/", admin_views.librarian_dashboard, name="librarian_dashboard"),
    path("manage/books/", admin_views.manage_books, name="manage_books"),
    path("manage/books/add/", admin_views.book_create, name="book_create"),
    path("manage/books/<int:pk>/edit/", admin_views.book_update, name="book_update"),
    path("manage/books/<int:pk>/delete/", admin_views.book_delete, name="book_delete"),
    path("manage/fines/", admin_views.manage_fines, name="manage_fines"),
    path("manage/fines/<int:fine_id>/pay/", admin_views.mark_fine_paid, name="mark_fine_paid"),
    path("manage/reports/", admin_views.reports_view, name="reports"),
    path("manage/users/", admin_views.monitor_users, name="monitor_users"),
]