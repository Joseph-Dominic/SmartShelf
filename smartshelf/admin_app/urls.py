from django.urls import path

from . import views

app_name = "admin_app"

urlpatterns = [
    path("dashboard/", views.librarian_dashboard, name="librarian_dashboard"),
    path("books/", views.manage_books, name="manage_books"),
    path("books/add/", views.book_create, name="book_create"),
    path("books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("fines/", views.manage_fines, name="manage_fines"),
    path("fines/<int:fine_id>/pay/", views.mark_fine_paid, name="mark_fine_paid"),
    path("reports/", views.reports_view, name="reports"),
    path("users/", views.monitor_users, name="monitor_users"),
]
