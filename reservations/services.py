import logging
from datetime import date

from django.db import transaction
from rest_framework.exceptions import NotFound

from .exceptions import OverlapConflict
from .models import Block, Booking, Property

logger = logging.getLogger("reservations")


def ranges_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """Whether two inclusive closed date ranges share at least one day."""
    return start_a <= end_b and start_b <= end_a


def _overlapping_bookings(property_id, start_date, end_date, *, exclude_booking_id=None):
    qs = Booking.objects.filter(
        property_id=property_id,
        status=Booking.Status.CONFIRMED,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_booking_id is not None:
        qs = qs.exclude(pk=exclude_booking_id)
    return qs


def _overlapping_blocks(property_id, start_date, end_date, *, exclude_block_id=None):
    qs = Block.objects.filter(
        property_id=property_id,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_block_id is not None:
        qs = qs.exclude(pk=exclude_block_id)
    return qs


def _assert_no_overlap(property_id, start_date, end_date, *, exclude_booking_id=None, exclude_block_id=None):
    booking_clash = _overlapping_bookings(
        property_id, start_date, end_date, exclude_booking_id=exclude_booking_id
    ).exists()
    block_clash = _overlapping_blocks(
        property_id, start_date, end_date, exclude_block_id=exclude_block_id
    ).exists()
    if booking_clash or block_clash:
        logger.warning(
            "Overlap rejected: property=%s range=%s..%s (booking_clash=%s block_clash=%s)",
            property_id, start_date, end_date, booking_clash, block_clash,
        )
        raise OverlapConflict()


def _get_property_locked(property_id) -> Property:
    """Fetch and row-lock a property, or raise 404 if it does not exist."""
    try:
        return Property.objects.select_for_update().get(pk=property_id)
    except Property.DoesNotExist:
        raise NotFound(f"Property {property_id} not found.")


def create_property(*, name: str, country_code: str) -> Property:
    return Property.objects.create(name=name, country_code=country_code)


@transaction.atomic
def create_booking(*, property_id, guest_name: str, start_date: date, end_date: date) -> Booking:
    prop = _get_property_locked(property_id)
    _assert_no_overlap(prop.id, start_date, end_date)
    booking = Booking.objects.create(
        property=prop,
        guest_name=guest_name,
        start_date=start_date,
        end_date=end_date,
        status=Booking.Status.CONFIRMED,
    )
    logger.info(
        "Booking created id=%s property=%s %s..%s",
        booking.id, prop.id, start_date, end_date,
    )
    return booking


@transaction.atomic
def update_booking(booking: Booking, *, guest_name=None, start_date=None, end_date=None) -> Booking:
    _get_property_locked(booking.property_id)

    new_start = start_date if start_date is not None else booking.start_date
    new_end = end_date if end_date is not None else booking.end_date

    if booking.status == Booking.Status.CONFIRMED:
        _assert_no_overlap(
            booking.property_id, new_start, new_end, exclude_booking_id=booking.id
        )

    if guest_name is not None:
        booking.guest_name = guest_name
    booking.start_date = new_start
    booking.end_date = new_end
    booking.save()
    logger.info("Booking updated id=%s %s..%s", booking.id, new_start, new_end)
    return booking


@transaction.atomic
def cancel_booking(booking: Booking) -> Booking:
    if booking.status != Booking.Status.CANCELED:
        booking.status = Booking.Status.CANCELED
        booking.save(update_fields=["status"])
        logger.info("Booking canceled id=%s", booking.id)
    return booking


@transaction.atomic
def rebook_booking(booking: Booking) -> Booking:
    """Revive a canceled booking at its original dates, re-running the check."""
    _get_property_locked(booking.property_id)
    _assert_no_overlap(
        booking.property_id,
        booking.start_date,
        booking.end_date,
        exclude_booking_id=booking.id,
    )
    if booking.status != Booking.Status.CONFIRMED:
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status"])
        logger.info("Booking rebooked id=%s", booking.id)
    return booking


def delete_booking(booking: Booking) -> None:
    booking_id = booking.id
    booking.delete()
    logger.info("Booking deleted id=%s", booking_id)


@transaction.atomic
def create_block(*, property_id, start_date: date, end_date: date) -> Block:
    prop = _get_property_locked(property_id)
    _assert_no_overlap(prop.id, start_date, end_date)
    block = Block.objects.create(property=prop, start_date=start_date, end_date=end_date)
    logger.info("Block created id=%s property=%s %s..%s", block.id, prop.id, start_date, end_date)
    return block


@transaction.atomic
def update_block(block: Block, *, start_date=None, end_date=None) -> Block:
    _get_property_locked(block.property_id)

    new_start = start_date if start_date is not None else block.start_date
    new_end = end_date if end_date is not None else block.end_date

    _assert_no_overlap(
        block.property_id, new_start, new_end, exclude_block_id=block.id
    )

    block.start_date = new_start
    block.end_date = new_end
    block.save()
    logger.info("Block updated id=%s %s..%s", block.id, new_start, new_end)
    return block


def delete_block(block: Block) -> None:
    block_id = block.id
    block.delete()
    logger.info("Block deleted id=%s", block_id)
