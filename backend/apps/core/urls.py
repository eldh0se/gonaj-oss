"""URL routes for the core app."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.api_root, name="api-root"),
]
