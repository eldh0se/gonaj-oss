"""Admin review surface for the transit dataset (constitution VII).

Curation and anomaly review happen here; bulk loading is the import
command's job (constitution VI).
"""
from django.contrib import admin

from .models import (
    ImportAnomaly,
    ImportRun,
    OsmSnapshot,
    Route,
    RouteMaster,
    RouteMasterMembership,
    RouteStopMembership,
    Stop,
)


@admin.register(OsmSnapshot)
class OsmSnapshotAdmin(admin.ModelAdmin):
    list_display = ("label", "recipe_ref", "retrieved_at", "imported_at")
    readonly_fields = ("label", "recipe_ref", "source_timestamps")


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("osm_id", "name", "lat", "lon")
    search_fields = ("name", "osm_id")


@admin.register(RouteMaster)
class RouteMasterAdmin(admin.ModelAdmin):
    list_display = ("osm_id", "name", "operator", "network", "verdict")
    list_filter = ("verdict", "network")
    search_fields = ("name", "osm_id")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("osm_id", "name", "from_text", "to_text", "verdict", "quarantined")
    list_filter = ("verdict", "quarantined")


@admin.register(RouteStopMembership)
class RouteStopMembershipAdmin(admin.ModelAdmin):
    list_display = ("route", "stop", "position", "source_index")


@admin.register(RouteMasterMembership)
class RouteMasterMembershipAdmin(admin.ModelAdmin):
    list_display = ("route_master", "route", "position", "source_index")


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ("pk", "snapshot", "started_at", "finished_at", "outcome")
    list_filter = ("outcome",)


@admin.register(ImportAnomaly)
class ImportAnomalyAdmin(admin.ModelAdmin):
    list_display = ("code", "severity", "entity_osm_type", "entity_osm_id", "run")
    list_filter = ("severity", "code")
