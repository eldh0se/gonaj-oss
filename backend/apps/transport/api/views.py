"""Public read-only transport API (FR-001–FR-003).

GET-only views with ``AllowAny`` and no authentication or tracking.
Routes served are exactly the servable dataset: non-quarantined
routes that belong to a master; every stop row is servable. The
public ``id`` is the stored row's surrogate ``id``; OSM identifiers
are never exposed.
"""
import math

from django.db.models import F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, NullIf, Trim
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.transport.models import (
    Route,
    RouteMasterMembership,
    RouteStopMembership,
    Stop,
)

from .errors import PlainBadRequest, PlainNotFound
from .pagination import SharedEnvelopePagination
from .serializers import (
    ConnectivityResultSerializer,
    RouteDetailSerializer,
    RouteListSerializer,
    StopDetailSerializer,
    StopListSerializer,
)
from .throttling import READ_THROTTLE_CLASSES

MAX_BBOX_SPAN_DEGREES = 0.5


def servable_routes():
    """Non-quarantined routes belonging to a master (T008)."""
    return Route.objects.filter(
        quarantined=False,
        master_memberships__isnull=False,
    )


def first_membership_position():
    """Earliest master-membership position of a route (T036)."""
    return Subquery(
        RouteMasterMembership.objects.filter(route=OuterRef("pk"))
        .order_by("position")
        .values("position")[:1]
    )


def order_routes(queryset):
    """Stored order (membership position, then id) that is safe
    under SELECT DISTINCT on every database (T036).

    Ordering resolves to the ``_mm_position`` annotation — a
    selected output — instead of a joined column, which PostgreSQL
    rejects under DISTINCT while SQLite silently permits.
    """
    return queryset.annotate(_mm_position=first_membership_position()
                            ).order_by("_mm_position", "id")


def routes_with_master_fields(queryset):
    """Annotate the passenger-facing operator/network from the master."""
    membership = RouteMasterMembership.objects.filter(
        route=OuterRef("pk")
    ).order_by("position")
    return queryset.annotate(
        operator=Subquery(
            membership.values("route_master__operator")[:1]
        ),
        network=Subquery(membership.values("route_master__network")[:1]),
    )


def endpoint_stop_name(ordering):
    """Name of the first/last ordered stop of a route (006)."""
    return Subquery(
        RouteStopMembership.objects.filter(route=OuterRef("pk"))
        .order_by(ordering)
        .values("stop__name")[:1]
    )


def routes_with_endpoint_names(queryset):
    """Resolved origin/destination: stored text wins (006).

    Null, empty, and whitespace-only stored text counts as
    absent and falls back to the endpoint stop names; routes
    without stops resolve to null (never invented).
    """
    blank = Value("")
    return queryset.annotate(
        resolved_origin=Coalesce(
            NullIf(Trim("from_text"), blank),
            endpoint_stop_name("position"),
        ),
        resolved_destination=Coalesce(
            NullIf(Trim("to_text"), blank),
            endpoint_stop_name("-position"),
        ),
    )


def paginated_response(queryset, request, serializer_class, extra=None):
    paginator = SharedEnvelopePagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(page, many=True)
    response = paginator.get_paginated_response(serializer.data)
    if extra:
        response.data.update(extra)
    return response


def route_not_found():
    return PlainNotFound(
        "We could not find that route. "
        "Please check the link and try again."
    )


def stop_not_found():
    return PlainNotFound(
        "We could not find that stop. "
        "Please check the link and try again."
    )


def connectivity_bad_request():
    return PlainBadRequest(
        "Please choose two different stops to check. "
        "Pick an origin stop and a destination stop and try again."
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def route_list(request):
    """Browse-all or search routes (FR-004–FR-006, FR-019)."""
    search = (request.query_params.get("search") or "").strip()
    operator = request.query_params.get("operator")
    network = request.query_params.get("network")

    queryset = routes_with_endpoint_names(
        routes_with_master_fields(servable_routes())
    )
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(from_text__icontains=search)
            | Q(to_text__icontains=search)
            | Q(
                stop_memberships__stop__name__icontains=search,
            )
            | Q(
                stop_memberships__stop__name_ml__icontains=search,
            )
        ).distinct()
    if operator is not None:
        queryset = queryset.filter(
            master_memberships__route_master__operator=operator
        ).distinct()
    if network is not None:
        queryset = queryset.filter(
            master_memberships__route_master__network=network
        ).distinct()
    queryset = order_routes(queryset).distinct()
    return paginated_response(queryset, request, RouteListSerializer)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def route_detail(request, pk):
    """Route detail with ordered stops (FR-013–FR-015)."""
    try:
        route = (
            routes_with_endpoint_names(
                routes_with_master_fields(servable_routes())
            )
            .distinct()
            .get(pk=pk)
        )
    except (Route.DoesNotExist, Route.MultipleObjectsReturned, ValueError):
        raise route_not_found()
    memberships = (
        RouteStopMembership.objects.filter(route=route)
        .select_related("stop")
        .order_by("position")
    )
    positions = [m.position for m in memberships]
    first, last = (min(positions), max(positions)) if positions else (None, None)
    steps = [
        {
            "stop": {
                "id": m.stop_id,
                "name": m.stop.name,
                "name_ml": m.stop.name_ml,
                "lat": m.stop.lat,
                "lon": m.stop.lon,
            },
            "position": m.position,
            "is_origin": m.position == first,
            "is_terminus": m.position == last,
        }
        for m in memberships
    ]
    payload = {
        "id": route.id,
        "name": route.name,
        "resolved_origin": route.resolved_origin,
        "resolved_destination": route.resolved_destination,
        "operator": route.operator,
        "network": route.network,
        "stops": steps,
    }
    return Response(RouteDetailSerializer(payload).data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def stop_list(request):
    """Stops by name or by map area — never both (FR-008–FR-011, FR-019)."""
    search = request.query_params.get("search")
    bbox = request.query_params.get("bbox")
    search_blank = search is None or not search.strip()

    if bbox is not None and not search_blank:
        raise PlainBadRequest(
            "Please search by stop name or by map area, not both "
            "at once. Clear one of them and try again."
        )
    if bbox is not None:
        try:
            parts = [v.strip() for v in bbox.split(",")]
            if len(parts) != 4 or any(not p for p in parts):
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
        except (TypeError, ValueError, AttributeError):
            raise PlainBadRequest(
                "That map area does not look right. Please give four "
                "coordinates as min_lon,min_lat,max_lon,max_lat and try "
                "again."
            )
        if (
            not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180)
            or not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90)
            or min_lon > max_lon
            or min_lat > max_lat
        ):
            raise PlainBadRequest(
                "That map area does not look right. Please give four "
                "coordinates as min_lon,min_lat,max_lon,max_lat and try "
                "again."
            )
        if (
            max_lon - min_lon > MAX_BBOX_SPAN_DEGREES
            or max_lat - min_lat > MAX_BBOX_SPAN_DEGREES
        ):
            return paginated_response(
                Stop.objects.none(),
                request,
                StopListSerializer,
                extra={
                    "status": "zoom_in",
                    "detail": (
                        "That area is too large to list stops for. "
                        "Please zoom in on the map and try again."
                    ),
                },
            )
        queryset = Stop.objects.filter(
            lon__gte=min_lon,
            lon__lte=max_lon,
            lat__gte=min_lat,
            lat__lte=max_lat,
        ).order_by("name", "id")
        if not queryset.exists():
            return paginated_response(
                queryset,
                request,
                StopListSerializer,
                extra={"status": "empty"},
            )
        return paginated_response(
            queryset, request, StopListSerializer, extra={"status": "ok"}
        )
    queryset = Stop.objects.all()
    if not search_blank:
        queryset = queryset.filter(
            Q(name__icontains=search.strip())
            | Q(name_ml__icontains=search.strip())
        )
    queryset = queryset.order_by("name", "id")
    return paginated_response(
        queryset, request, StopListSerializer, extra={"status": "ok"}
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def stop_detail(request, pk):
    """Stop detail with coordinates and serving routes (FR-012, FR-015)."""
    try:
        stop = Stop.objects.get(pk=pk)
    except (Stop.DoesNotExist, ValueError):
        raise stop_not_found()
    serving = order_routes(
        routes_with_master_fields(servable_routes()).filter(
            stop_memberships__stop=stop
        )
    ).distinct()
    payload = {
        "id": stop.id,
        "name": stop.name,
        "name_ml": stop.name_ml,
        "lat": stop.lat,
        "lon": stop.lon,
        "serving_routes": [
            {"id": r.id, "name": r.name} for r in serving
        ],
    }
    return Response(StopDetailSerializer(payload).data)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes(READ_THROTTLE_CLASSES)
def connectivity(request):
    """Direct routes containing both stops in order (FR-016–FR-018)."""
    raw_from = request.query_params.get("from")
    raw_to = request.query_params.get("to")
    try:
        from_id = int(raw_from) if raw_from is not None else None
        to_id = int(raw_to) if raw_to is not None else None
    except (TypeError, ValueError):
        raise connectivity_bad_request()
    if (
        from_id is None
        or to_id is None
        or from_id < 1
        or to_id < 1
        or from_id == to_id
    ):
        raise connectivity_bad_request()
    if not Stop.objects.filter(pk=from_id).exists() or not Stop.objects.filter(
        pk=to_id
    ).exists():
        raise connectivity_bad_request()

    origin_memberships = RouteStopMembership.objects.filter(
        route=OuterRef("pk"), stop_id=from_id
    )
    destination_memberships = RouteStopMembership.objects.filter(
        route=OuterRef("pk"), stop_id=to_id
    )
    queryset = (
        routes_with_endpoint_names(
            routes_with_master_fields(servable_routes())
        )
        .annotate(
            from_position=Subquery(
                origin_memberships.values("position")[:1]
            ),
            to_position=Subquery(
                destination_memberships.values("position")[:1]
            ),
        )
        .filter(
            from_position__isnull=False,
            to_position__isnull=False,
            from_position__lt=F("to_position"),
        )
    )
    queryset = order_routes(queryset).distinct()
    rows = [
        {
            "id": r.id,
            "name": r.name,
            "resolved_origin": r.resolved_origin,
            "resolved_destination": r.resolved_destination,
            "operator": r.operator,
            "network": r.network,
            "from_position": r.from_position,
            "to_position": r.to_position,
            "evidence": f"/api/v1/routes/{r.id}/",
        }
        for r in queryset
    ]
    paginator = SharedEnvelopePagination()
    paginator.page_number = paginator._page_param(request, "page", 1)
    requested_size = paginator._page_param(
        request, "page_size", paginator.default_page_size
    )
    paginator.page_size = min(requested_size, paginator.max_page_size)
    paginator.count = len(rows)
    paginator.total_pages = (
        math.ceil(paginator.count / paginator.page_size)
        if paginator.count
        else 0
    )
    start = (paginator.page_number - 1) * paginator.page_size
    page_rows = rows[start : start + paginator.page_size]
    serializer = ConnectivityResultSerializer(page_rows, many=True)
    return paginator.get_paginated_response(serializer.data)
