from rest_framework import serializers

from .models import Block, Booking, Property


def ensure_date_order(start, end):
    if start >= end:
        raise serializers.ValidationError({"end_date": "end_date must be after start_date."})


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ["id", "name", "country_code"]
        read_only_fields = ["id"]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "property", "guest_name", "start_date", "end_date", "status"]
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    property = serializers.IntegerField(min_value=1)
    guest_name = serializers.CharField(max_length=255)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        ensure_date_order(attrs["start_date"], attrs["end_date"])
        return attrs


class BookingUpdateSerializer(serializers.Serializer):
    guest_name = serializers.CharField(max_length=255, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        has_start = "start_date" in attrs
        has_end = "end_date" in attrs
        if has_start != has_end:
            raise serializers.ValidationError(
                "start_date and end_date must be provided together."
            )
        if has_start:
            ensure_date_order(attrs["start_date"], attrs["end_date"])
        return attrs


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ["id", "property", "start_date", "end_date"]
        read_only_fields = fields


class BlockCreateSerializer(serializers.Serializer):
    property = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        ensure_date_order(attrs["start_date"], attrs["end_date"])
        return attrs


class BlockUpdateSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        ensure_date_order(attrs["start_date"], attrs["end_date"])
        return attrs
