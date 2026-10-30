"""Root URLconf: internal admin plus the versioned public API."""
from django.contrib import admin
from django.urls import include, path

handler404 = "apps.transport.api.errors.api_not_found"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.transport.api.urls")),
    path("api/v1/", include("apps.journey.urls")),
]
