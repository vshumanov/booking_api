from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Block, Booking, Property
from .serializers import (
    BlockCreateSerializer,
    BlockSerializer,
    BlockUpdateSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    BookingUpdateSerializer,
    PropertySerializer,
)


class PropertyViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

    def perform_create(self, serializer):
        serializer.instance = services.create_property(**serializer.validated_data)


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Booking.objects.all().order_by("id")
    serializer_class = BookingSerializer
    action_serializers = {
        "create": BookingCreateSerializer,
        "update": BookingUpdateSerializer,
        "partial_update": BookingUpdateSerializer,
    }

    def get_serializer_class(self):
        return self.action_serializers.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking = services.create_booking(
            property_id=data["property"],
            guest_name=data["guest_name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        booking = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        booking = services.update_booking(booking, **serializer.validated_data)
        return Response(BookingSerializer(booking).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        services.delete_booking(booking)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        booking = services.cancel_booking(self.get_object())
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def rebook(self, request, *args, **kwargs):
        booking = services.rebook_booking(self.get_object())
        return Response(BookingSerializer(booking).data)


class BlockViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Block.objects.all().order_by("id")
    serializer_class = BlockSerializer
    action_serializers = {
        "create": BlockCreateSerializer,
        "update": BlockUpdateSerializer,
        "partial_update": BlockUpdateSerializer,
    }

    def get_serializer_class(self):
        return self.action_serializers.get(self.action, self.serializer_class)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        block = services.create_block(
            property_id=data["property"],
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        return Response(BlockSerializer(block).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        block = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        block = services.update_block(block, **serializer.validated_data)
        return Response(BlockSerializer(block).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        services.delete_block(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
