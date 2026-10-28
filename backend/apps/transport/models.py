"""Transit domain models: OSM-derived stops, routes, and masters.

Natural identity everywhere is (`osm_type`, `osm_id`). Every row
carries the import run that created it; the run carries the snapshot;
the snapshot carries the recipe reference (constitution V).
"""
from django.db import models


class Verdict(models.TextChoices):
    VALID = "VALID", "Valid"
    VALID_WITH_WARNING = "VALID_WITH_WARNING", "Valid with warning"
    MISSING_DATA = "MISSING_DATA", "Missing data"
    AMBIGUOUS = "AMBIGUOUS", "Ambiguous"
    UNRESOLVED = "UNRESOLVED", "Unresolved"


class Severity(models.TextChoices):
    FATAL = "fatal", "Fatal"
    WARNING = "warning", "Warning"
    INFO = "info", "Info"


class OsmSnapshot(models.Model):
    """One retained Overpass extract batch. Append-only."""

    label = models.CharField(max_length=255, unique=True)
    recipe_ref = models.CharField(max_length=512)
    source_timestamps = models.JSONField(default=dict)
    retrieved_at = models.DateTimeField()
    imported_at = models.DateTimeField()

    def __str__(self):
        return self.label


class Stop(models.Model):
    """A bus stop platform: an OSM node tagged highway=bus_stop."""

    import_run = models.ForeignKey(
        "ImportRun", on_delete=models.CASCADE, related_name="+"
    )
    osm_type = models.CharField(max_length=16, default="node")
    osm_id = models.BigIntegerField()
    name = models.CharField(max_length=255, null=True, blank=True)
    name_ml = models.CharField(max_length=255, null=True, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    tags = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["osm_type", "osm_id"], name="stop_natural_key"
            )
        ]
        indexes = [models.Index(fields=["lat", "lon"])]

    def __str__(self):
        return self.name or f"stop {self.osm_id}"


class RouteMaster(models.Model):
    """A route_master relation grouping direction variants."""

    import_run = models.ForeignKey(
        "ImportRun", on_delete=models.CASCADE, related_name="+"
    )
    osm_type = models.CharField(max_length=16, default="relation")
    osm_id = models.BigIntegerField()
    name = models.CharField(max_length=512)
    operator = models.CharField(max_length=255, null=True, blank=True)
    network = models.CharField(max_length=255, null=True, blank=True)
    verdict = models.CharField(
        max_length=24, choices=Verdict.choices, default=Verdict.VALID
    )
    warnings = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["osm_type", "osm_id"], name="routemaster_natural_key"
            )
        ]

    def __str__(self):
        return self.name


class Route(models.Model):
    """A route relation: one direction or variant of a master."""

    import_run = models.ForeignKey(
        "ImportRun", on_delete=models.CASCADE, related_name="+"
    )
    osm_type = models.CharField(max_length=16, default="relation")
    osm_id = models.BigIntegerField()
    name = models.CharField(max_length=512, null=True, blank=True)
    from_text = models.CharField(max_length=255, null=True, blank=True)
    to_text = models.CharField(max_length=255, null=True, blank=True)
    direction = models.SmallIntegerField(null=True, blank=True)
    verdict = models.CharField(
        max_length=24, choices=Verdict.choices, default=Verdict.VALID
    )
    quarantined = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["osm_type", "osm_id"], name="route_natural_key"
            )
        ]

    def __str__(self):
        return self.name or f"route {self.osm_id}"


class RouteStopMembership(models.Model):
    """Ordered platform membership of a route. Derived data: rebuilt
    on every import with contiguous 1-based positions."""

    import_run = models.ForeignKey(
        "ImportRun", on_delete=models.CASCADE, related_name="+"
    )
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="stop_memberships"
    )
    stop = models.ForeignKey(
        Stop, on_delete=models.CASCADE, related_name="route_memberships"
    )
    position = models.PositiveIntegerField()
    source_index = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["route", "position"],
                name="routestop_position_unique",
            )
        ]
        ordering = ["position"]


class RouteMasterMembership(models.Model):
    """Child-route membership of a master, preserving source order."""

    import_run = models.ForeignKey(
        "ImportRun", on_delete=models.CASCADE, related_name="+"
    )
    route_master = models.ForeignKey(
        RouteMaster,
        on_delete=models.CASCADE,
        related_name="child_memberships",
    )
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="master_memberships"
    )
    position = models.PositiveIntegerField()
    source_index = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["route_master", "position"],
                name="routemaster_position_unique",
            )
        ]
        ordering = ["position"]


class ImportRun(models.Model):
    """One execution of the import against one snapshot."""

    OUTCOME_RUNNING = "running"
    OUTCOME_SUCCEEDED = "succeeded"
    OUTCOME_ABORTED = "aborted"
    OUTCOME_CHOICES = [
        (OUTCOME_RUNNING, "Running"),
        (OUTCOME_SUCCEEDED, "Succeeded"),
        (OUTCOME_ABORTED, "Aborted"),
    ]

    snapshot = models.ForeignKey(
        OsmSnapshot, on_delete=models.CASCADE, related_name="runs"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(
        max_length=16, choices=OUTCOME_CHOICES, default=OUTCOME_RUNNING
    )

    def __str__(self):
        return f"run {self.pk} ({self.outcome})"


class ImportAnomaly(models.Model):
    """One recorded deviation. Immutable once written: flagged,
    quarantined, or blocking — never silently repaired."""

    run = models.ForeignKey(
        ImportRun, on_delete=models.CASCADE, related_name="anomalies"
    )
    severity = models.CharField(max_length=16, choices=Severity.choices)
    code = models.CharField(max_length=64)
    entity_osm_type = models.CharField(
        max_length=16, null=True, blank=True
    )
    entity_osm_id = models.BigIntegerField(null=True, blank=True)
    detail = models.TextField()

    def __str__(self):
        return f"{self.severity}:{self.code}"
