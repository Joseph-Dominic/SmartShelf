from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    # Catalog
    path("", views.book_list_view, name="book_list"),
    path("books/<int:pk>/", views.book_detail_view, name="book_detail"),
    path("books/<int:pk>/borrow/", views.borrow_book_view, name="borrow_book"),
    path("books/<int:pk>/reserve/", views.place_reservation_view, name="place_reservation"),
    path("reservations/<int:pk>/cancel/", views.cancel_reservation_view, name="cancel_reservation"),

    # Borrower Portal
    path("my-loans/", views.user_loans_view, name="user_loans"),
    path("loans/<int:pk>/renew/", views.renew_loan_view, name="renew_loan"),

    # Circulation Desk
    path("desk/", views.librarian_dashboard_view, name="librarian_dashboard"),
    path("desk/dashboard/", views.librarian_dashboard_view, name="dashboard"),
    path("desk/issue/", views.issue_book_copy_view, name="issue_book"),
    path("desk/return/<int:loan_id>/", views.return_book_copy_view, name="return_book"),

    # Inventory Management & CRUD
    path("desk/books/", views.manage_books_view, name="manage_books"),
    path("desk/books/manage/", views.manage_books_view, name="book_manage"),
    path("desk/books/create/", views.book_create_view, name="book_create"),
    path("desk/books/<int:pk>/edit/", views.book_update_view, name="book_update"),
    path("desk/books/<int:pk>/delete/", views.book_delete_view, name="book_delete"),

    # Fines
    path("desk/fines/", views.manage_fines_view, name="manage_fines"),
    path("desk/fines/list/", views.manage_fines_view, name="fine_list"),
    path("desk/fines/<int:fine_id>/settle/", views.settle_fine_view, name="settle_fine"),

    # Reports & Monitoring
    path("desk/reports/", views.reports_view, name="reports"),
    path("desk/users/", views.user_monitor_view, name="user_monitor"),
]
