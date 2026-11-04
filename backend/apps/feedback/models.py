"""Anonymous passenger feedback reports for human curation."""

from django.db import models

CATEGORY_CHOICES = (
    ("incorrect", "incorrect"),
    ("missing", "missing"),
    ("outdated", "outdated"),
    ("other", "other"),
)

STATUS_CHOICES = (
    ("new", "new"),
    ("reviewed", "reviewed"),
    ("dismissed", "dismissed"),
)


class FeedbackReport(models.Model):
    """A passenger's report. Write-once from the public endpoint; status
    transitions happen in Django Admin only."""

    reference = models.CharField(max_length=11, unique=True)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES)
    message = models.TextField()
    route = models.ForeignKey(
        "transport.Route", null=True, blank=True, on_delete=models.SET_NULL
    )
    stop = models.ForeignKey(
        "transport.Stop", null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"])]
