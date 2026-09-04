from django.urls import path
from . import views

app_name = "library"

urlpatterns = [
    # Catalog & Holds
    path("", views.book_list_view, name="book_list"),
    path("books/<int:pk>/", views.book_detail_view, name="book_detail"),
    path("books/<int:pk>/reserve/", views.place_reservation_view, name="place_reservation"),
    path("reservations/<int:pk>/cancel/", views.cancel_reservation_view, name="cancel_reservation"),

    # Borrower Portal & Renewals
    path("my-loans/", views.user_loans_view, name="user_loans"),
    path("loans/<int:pk>/renew/", views.renew_loan_view, name="renew_loan"),

    # Librarian Circulation Desk (aliased to prevent NoReverseMatch)
    path("desk/", views.librarian_dashboard_view, name="librarian_dashboard"),
    path("desk/dashboard/", views.librarian_dashboard_view, name="dashboard"),
    path("desk/books/", views.manage_books_view, name="manage_books"),
    path("desk/books/manage/", views.manage_books_view, name="book_manage"),
    path("desk/fines/", views.manage_fines_view, name="manage_fines"),
    path("desk/fines/list/", views.manage_fines_view, name="fine_list"),
    path("desk/fines/<int:fine_id>/settle/", views.settle_fine_view, name="settle_fine"),
    path("desk/issue/", views.issue_book_copy_view, name="issue_book"),
    path("desk/return/<int:loan_id>/", views.return_book_copy_view, name="return_book"),
]