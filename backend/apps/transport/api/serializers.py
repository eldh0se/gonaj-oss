"""Public read serializers: whitelisted fields only (FR-007).

``tags``, ``osm_type``, ``osm_id``, ``import_run``, ``verdict``,
``quarantined``, ``direction``, ``source_index``, and every master
object are structurally absent — new internal fields cannot leak
by accident because only the fields below are ever rendered.
"""
from rest_framework import serializers

from apps.transport.models import Route, Stop


class RouteListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    origin = serializers.CharField(source="from_text", allow_null=True)
    destination = serializers.CharField(source="to_text", allow_null=True)
    operator = serializers.CharField(allow_null=True)
    network = serializers.CharField(allow_null=True)


class StopListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = ("id", "name", "name_ml", "lat", "lon")


class RouteStopStepSerializer(serializers.Serializer):
    stop = StopListSerializer()
    position = serializers.IntegerField()
    is_origin = serializers.BooleanField()
    is_terminus = serializers.BooleanField()


class RouteDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    origin = serializers.CharField(source="from_text", allow_null=True)
    destination = serializers.CharField(source="to_text", allow_null=True)
    operator = serializers.CharField(allow_null=True)
    network = serializers.CharField(allow_null=True)
    stops = RouteStopStepSerializer(many=True)


class ServingRouteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)


class StopDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    name_ml = serializers.CharField(allow_null=True)
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    serving_routes = ServingRouteSerializer(many=True)


class ConnectivityResultSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    origin = serializers.CharField(source="from_text", allow_null=True)
    destination = serializers.CharField(source="to_text", allow_null=True)
    operator = serializers.CharField(allow_null=True)
    network = serializers.CharField(allow_null=True)
    from_position = serializers.IntegerField()
    to_position = serializers.IntegerField()
    evidence = serializers.CharField()
