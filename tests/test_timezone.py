from datetime import date

import pytest
from django.test import override_settings

from reservations import services
from reservations.exceptions import OverlapConflict
from reservations.models import Property

# Extremes: UTC+14, UTC, and UTC-8. If a DateField or the overlap check
# depended on the server timezone, these would disagree.
TIMEZONES = ["Pacific/Kiritimati", "UTC", "America/Los_Angeles"]


def d(day: int) -> date:
    return date(2026, 1, day)


@pytest.mark.django_db
@pytest.mark.parametrize("tz", TIMEZONES)
def test_date_field_does_not_shift(tz):
    with override_settings(TIME_ZONE=tz):
        prop = Property.objects.create(name="Reef", country_code="KI")
        booking = services.create_booking(
            property_id=prop.id, guest_name="Ada", start_date=d(10), end_date=d(12)
        )
        booking.refresh_from_db()
        assert booking.start_date == d(10)
        assert booking.end_date == d(12)


@pytest.mark.django_db
@pytest.mark.parametrize("tz", TIMEZONES)
def test_overlap_decision_is_timezone_independent(tz):
    with override_settings(TIME_ZONE=tz):
        prop = Property.objects.create(name="Reef", country_code="KI")
        services.create_booking(
            property_id=prop.id, guest_name="Ada", start_date=d(10), end_date=d(15)
        )
        # Boundary touch on day 15 must be rejected in every timezone.
        with pytest.raises(OverlapConflict):
            services.create_booking(
                property_id=prop.id, guest_name="Bob", start_date=d(15), end_date=d(18)
            )
        # Non-touching range must be accepted in every timezone.
        ok = services.create_booking(
            property_id=prop.id, guest_name="Cy", start_date=d(16), end_date=d(18)
        )
        assert ok.pk is not None
