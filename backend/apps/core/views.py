"""Cross-cutting API views (version discovery today)."""
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def api_root(request):
    """Version discovery root; see contracts/api-root.md."""
    return Response({"name": "gonaj", "version": "v1"})
