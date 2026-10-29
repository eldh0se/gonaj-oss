"""Hand-built factories for the read API tests (T006).

Small deterministic graphs — no import fixtures needed — covering
servable, quarantined, orphan, duplicate-name, duplicate-platform,
single-stop, and membership-empty cases for all story tests.
"""
from django.core.cache import caches
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.throttling import SimpleRateThrottle

from apps.transport.models import (
    ImportRun,
    OsmSnapshot,
    Route,
    RouteMaster,
    RouteMasterMembership,
    RouteStopMembership,
    Stop,
)


def make_snapshot(label="factory-sample"):
    now = timezone.now()
    snapshot = OsmSnapshot.objects.create(
        label=label,
        recipe_ref="specs/002-osm-snapshot-import/spec.md",
        source_timestamps={},
        retrieved_at=now,
        imported_at=now,
    )
    run = ImportRun.objects.create(
        snapshot=snapshot, finished_at=now, outcome="succeeded"
    )
    return snapshot, run


def make_stop(run, osm_id, name, lat, lon, name_ml=None):
    return Stop.objects.create(
        import_run=run,
        osm_type="node",
        osm_id=osm_id,
        name=name,
        name_ml=name_ml,
        lat=lat,
        lon=lon,
        tags={},
    )


def make_master(run, osm_id, name, operator=None, network=None):
    return RouteMaster.objects.create(
        import_run=run,
        osm_type="relation",
        osm_id=osm_id,
        name=name,
        operator=operator,
        network=network,
        verdict="VALID",
        warnings=[],
    )


def make_route(
    run,
    osm_id,
    name,
    from_text=None,
    to_text=None,
    quarantined=False,
):
    return Route.objects.create(
        import_run=run,
        osm_type="relation",
        osm_id=osm_id,
        name=name,
        from_text=from_text,
        to_text=to_text,
        verdict="VALID",
        quarantined=quarantined,
    )


def link_master(run, master, route, position, source_index=None):
    return RouteMasterMembership.objects.create(
        import_run=run,
        route_master=master,
        route=route,
        position=position,
        source_index=position if source_index is None else source_index,
    )


def link_stop(run, route, stop, position, source_index=None):
    return RouteStopMembership.objects.create(
        import_run=run,
        route=route,
        stop=stop,
        position=position,
        source_index=position if source_index is None else source_index,
    )


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache"
        }
    }
)
class ApiTestCase(TestCase):
    """Base for read-API tests: isolate throttle counters per test.

    DRF throttles bind the default cache connection at import time,
    so the production database cache (which needs `createcachetable`
    on a real database) is swapped for an isolated in-memory
    backend here. Behaviour under test is identical: hashed keys,
    shared budgets, and expiry windows are backend-independent.
    """

    def setUp(self):
        super().setUp()
        self._real_throttle_cache = SimpleRateThrottle.cache
        test_cache = caches["default"]
        test_cache.clear()
        SimpleRateThrottle.cache = test_cache
        self.addCleanup(
            setattr, SimpleRateThrottle, "cache",
            self._real_throttle_cache)
