from datetime import date

import pytest
from rest_framework.exceptions import NotFound

from reservations import services
from reservations.exceptions import OverlapConflict
from reservations.models import Block, Booking, Property


def d(day: int) -> date:
    return date(2026, 1, day)


# Existing occupies days 11..16 (the spec table's reference range).
EXISTING = (d(11), d(16))


@pytest.mark.parametrize(
    "new_range, expected",
    [
        ((d(8), d(10)), False),   # before, no touch
        ((d(17), d(19)), False),  # after, no touch
        ((d(13), d(15)), True),   # fully inside
        ((d(8), d(11)), True),    # touches only start boundary
        ((d(16), d(18)), True),   # touches only end boundary
        ((d(10), d(17)), True),   # fully contains existing
        ((d(11), d(16)), True),   # identical
        ((d(8), d(12)), True),    # straddles start
        ((d(15), d(20)), True),   # straddles end
    ],
)
def test_ranges_overlap_boundaries(new_range, expected):
    assert services.ranges_overlap(*new_range, *EXISTING) is expected


def test_ranges_overlap_is_symmetric():
    assert services.ranges_overlap(*EXISTING, d(13), d(15)) == services.ranges_overlap(
        d(13), d(15), *EXISTING
    )


@pytest.fixture
def prop(db):
    return Property.objects.create(name="Beach House", country_code="US")


def make_booking(prop, start, end, status=Booking.Status.CONFIRMED):
    return Booking.objects.create(
        property=prop, guest_name="Ada", start_date=start, end_date=end, status=status
    )


def test_create_booking_success(prop):
    booking = services.create_booking(
        property_id=prop.id, guest_name="Ada", start_date=d(10), end_date=d(12)
    )
    assert booking.pk is not None
    assert booking.status == Booking.Status.CONFIRMED


def test_create_booking_overlapping_confirmed_rejected(prop):
    make_booking(prop, d(10), d(15))
    with pytest.raises(OverlapConflict):
        services.create_booking(
            property_id=prop.id, guest_name="Bob", start_date=d(13), end_date=d(18)
        )


def test_create_booking_touching_boundary_rejected(prop):
    make_booking(prop, d(10), d(15))
    with pytest.raises(OverlapConflict):
        services.create_booking(
            property_id=prop.id, guest_name="Bob", start_date=d(15), end_date=d(18)
        )


def test_create_booking_adjacent_non_touching_allowed(prop):
    make_booking(prop, d(10), d(15))
    booking = services.create_booking(
        property_id=prop.id, guest_name="Bob", start_date=d(16), end_date=d(18)
    )
    assert booking.pk is not None


def test_create_booking_overlapping_block_rejected(prop):
    Block.objects.create(property=prop, start_date=d(10), end_date=d(15))
    with pytest.raises(OverlapConflict):
        services.create_booking(
            property_id=prop.id, guest_name="Bob", start_date=d(12), end_date=d(14)
        )


def test_create_booking_ignores_canceled(prop):
    make_booking(prop, d(10), d(15), status=Booking.Status.CANCELED)
    booking = services.create_booking(
        property_id=prop.id, guest_name="Bob", start_date=d(11), end_date=d(14)
    )
    assert booking.pk is not None


def test_create_booking_other_property_allowed(prop):
    other = Property.objects.create(name="Cabin", country_code="CA")
    make_booking(prop, d(10), d(15))
    booking = services.create_booking(
        property_id=other.id, guest_name="Bob", start_date=d(10), end_date=d(15)
    )
    assert booking.pk is not None


def test_create_booking_missing_property_404(db):
    with pytest.raises(NotFound):
        services.create_booking(
            property_id=9999, guest_name="Bob", start_date=d(10), end_date=d(12)
        )


def test_create_block_overlapping_booking_rejected(prop):
    make_booking(prop, d(10), d(15))
    with pytest.raises(OverlapConflict):
        services.create_block(property_id=prop.id, start_date=d(12), end_date=d(14))


def test_create_block_overlapping_block_rejected(prop):
    Block.objects.create(property=prop, start_date=d(10), end_date=d(15))
    with pytest.raises(OverlapConflict):
        services.create_block(property_id=prop.id, start_date=d(15), end_date=d(18))


def test_update_booking_self_exclusion(prop):
    booking = make_booking(prop, d(10), d(15))
    updated = services.update_booking(booking, start_date=d(11), end_date=d(16))
    assert updated.start_date == d(11)
    assert updated.end_date == d(16)


def test_update_booking_guest_only(prop):
    booking = make_booking(prop, d(10), d(15))
    updated = services.update_booking(booking, guest_name="Grace")
    assert updated.guest_name == "Grace"
    assert updated.start_date == d(10)


def test_update_booking_into_other_rejected(prop):
    make_booking(prop, d(20), d(25))
    booking = make_booking(prop, d(10), d(15))
    with pytest.raises(OverlapConflict):
        services.update_booking(booking, start_date=d(18), end_date=d(22))


def test_update_canceled_booking_skips_overlap_check(prop):
    make_booking(prop, d(10), d(15))
    canceled = make_booking(prop, d(1), d(2), status=Booking.Status.CANCELED)
    updated = services.update_booking(canceled, start_date=d(11), end_date=d(14))
    assert updated.start_date == d(11)


def test_cancel_frees_dates(prop):
    booking = make_booking(prop, d(10), d(15))
    services.cancel_booking(booking)
    assert booking.status == Booking.Status.CANCELED
    again = services.create_booking(
        property_id=prop.id, guest_name="Bob", start_date=d(10), end_date=d(15)
    )
    assert again.pk is not None


def test_cancel_is_idempotent(prop):
    booking = make_booking(prop, d(10), d(15), status=Booking.Status.CANCELED)
    result = services.cancel_booking(booking)
    assert result.status == Booking.Status.CANCELED


def test_rebook_success_when_free(prop):
    booking = make_booking(prop, d(10), d(15), status=Booking.Status.CANCELED)
    result = services.rebook_booking(booking)
    assert result.status == Booking.Status.CONFIRMED


def test_rebook_rejected_when_dates_taken(prop):
    canceled = make_booking(prop, d(10), d(15), status=Booking.Status.CANCELED)
    make_booking(prop, d(12), d(18))
    with pytest.raises(OverlapConflict):
        services.rebook_booking(canceled)
    canceled.refresh_from_db()
    assert canceled.status == Booking.Status.CANCELED


def test_delete_booking_removes_row(prop):
    booking = make_booking(prop, d(10), d(15))
    booking_id = booking.id
    services.delete_booking(booking)
    assert not Booking.objects.filter(pk=booking_id).exists()


def test_update_block_self_exclusion(prop):
    block = Block.objects.create(property=prop, start_date=d(10), end_date=d(15))
    updated = services.update_block(block, start_date=d(11), end_date=d(16))
    assert updated.end_date == d(16)
