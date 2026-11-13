from hypothesis import given
from hypothesis import strategies as st

from reservations.countries import ISO_3166_1_ALPHA2
from reservations.serializers import (
    BlockCreateSerializer,
    BlockUpdateSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
    PropertySerializer,
)

dates = st.dates()
iso_codes = st.sampled_from(sorted(ISO_3166_1_ALPHA2))
safe_text = st.text(st.characters(min_codepoint=32, codec="utf-8"), max_size=255)


@given(code=st.text(max_size=6))
def test_property_country_code_valid_iff_real_code(code):
    s = PropertySerializer(data={"name": "Beach House", "country_code": code})
    assert s.is_valid() is (code in ISO_3166_1_ALPHA2)


@given(code=iso_codes)
def test_property_accepts_every_real_code(code):
    s = PropertySerializer(data={"name": "Beach House", "country_code": code})
    assert s.is_valid(), s.errors


@given(name=safe_text)
def test_property_name_rejects_blank(name):
    s = PropertySerializer(data={"name": name, "country_code": "US"})
    assert s.is_valid() is bool(name.strip())


def test_property_name_rejects_null_char():
    s = PropertySerializer(data={"name": "a\x00b", "country_code": "US"})
    assert not s.is_valid()


@given(start=dates, end=dates)
def test_booking_create_valid_iff_start_before_end(start, end):
    s = BookingCreateSerializer(
        data={
            "property": 1,
            "guest_name": "Ada",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
    )
    assert s.is_valid() is (start < end)


@given(
    prop=st.integers(min_value=-5, max_value=5),
    start=dates,
    end=dates,
)
def test_booking_create_property_must_be_positive(prop, start, end):
    s = BookingCreateSerializer(
        data={
            "property": prop,
            "guest_name": "Ada",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
    )
    expected = prop >= 1 and start < end
    assert s.is_valid() is expected


@given(
    guest=st.none() | safe_text,
    start=st.none() | dates,
    end=st.none() | dates,
)
def test_booking_update_fuzz(guest, start, end):
    data = {}
    if guest is not None:
        data["guest_name"] = guest
    if start is not None:
        data["start_date"] = start.isoformat()
    if end is not None:
        data["end_date"] = end.isoformat()

    if (start is None) != (end is None):
        expected = False
    elif start is not None:
        expected = start < end
    else:
        expected = True
    if guest is not None and not guest.strip():
        expected = False

    s = BookingUpdateSerializer(data=data)
    assert s.is_valid() is expected, (data, dict(s.errors))


@given(start=dates, end=dates)
def test_block_create_valid_iff_start_before_end(start, end):
    s = BlockCreateSerializer(
        data={"property": 1, "start_date": start.isoformat(), "end_date": end.isoformat()}
    )
    assert s.is_valid() is (start < end)


@given(start=dates, end=dates)
def test_block_update_valid_iff_start_before_end(start, end):
    s = BlockUpdateSerializer(
        data={"start_date": start.isoformat(), "end_date": end.isoformat()}
    )
    assert s.is_valid() is (start < end)


def test_booking_update_paired_dates_message():
    s = BookingUpdateSerializer(data={"start_date": "2026-01-10"})
    assert not s.is_valid()
    assert "together" in str(s.errors["non_field_errors"][0])


def test_booking_create_missing_fields_reported():
    s = BookingCreateSerializer(data={"property": 1})
    assert not s.is_valid()
    assert set(s.errors) == {"guest_name", "start_date", "end_date"}
