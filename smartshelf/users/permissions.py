# smartshelf/users/permissions.py
from django.core.exceptions import PermissionDenied
from functools import wraps

def librarian_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_librarian:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("Access restricted to library administrators.")
    return _wrapped_view

def borrower_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You must be logged in to access borrower features.")
    return _wrapped_view