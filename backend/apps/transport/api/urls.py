"""URL routes for the public read-only transport API."""
from django.urls import path

from . import views

urlpatterns = [
    path("routes/", views.route_list, name="route-list"),
    path("routes/<int:pk>/", views.route_detail, name="route-detail"),
    path("stops/", views.stop_list, name="stop-list"),
    path("stops/<int:pk>/", views.stop_detail, name="stop-detail"),
    path("connectivity/", views.connectivity, name="connectivity"),
]
