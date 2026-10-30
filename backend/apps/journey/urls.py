"""URL routes for the journey helper."""
from django.urls import path

from . import views

urlpatterns = [
    path("journey/", views.journey, name="journey"),
    path("journey/transcribe/", views.transcribe, name="journey-transcribe"),
]
