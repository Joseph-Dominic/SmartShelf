from django.urls import path

from . import views

app_name = "admin_app"

urlpatterns = [
    path("dashboard/", views.librarian_dashboard, name="librarian_dashboard"),
    path("books/", views.manage_books, name="manage_books"),
    path("books/add/", views.book_create, name="book_create"),
    path("authors/add/", views.author_create, name="author_create"),
    path("authors/", views.manage_authors, name="manage_authors"),
    path("authors/<int:pk>/edit/", views.author_update, name="author_update"),
    path("authors/<int:pk>/delete/", views.author_delete, name="author_delete"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/", views.manage_categories, name="manage_categories"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("books/<int:pk>/stock/", views.book_stock_manage, name="book_stock"),
    path("books/<int:pk>/stock/add/", views.book_stock_add, name="book_stock_add"),
    path("copies/<int:pk>/update/", views.book_copy_update, name="book_copy_update"),
    path("copies/<int:pk>/delete/", views.book_copy_delete, name="book_copy_delete"),
    path("fines/", views.manage_fines, name="manage_fines"),
    path("fines/<int:fine_id>/pay/", views.mark_fine_paid, name="mark_fine_paid"),
    path("reports/", views.reports_view, name="reports"),
    path("users/", views.monitor_users, name="monitor_users"),
]
