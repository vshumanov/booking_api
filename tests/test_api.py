from datetime import date

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient

from reservations.countries import ISO_3166_1_ALPHA2
from reservations.services import ranges_overlap

PROPERTIES = "/api/v1/properties/"
BOOKINGS = "/api/v1/bookings/"
BLOCKS = "/api/v1/blocks/"


def iso(day: int) -> str:
    return date(2026, 1, day).isoformat()


def book(client, property_id, start, end, guest="Ada"):
    return client.post(
        BOOKINGS,
        {"property": property_id, "guest_name": guest,
         "start_date": iso(start), "end_date": iso(end)},
        format="json",
    )


def block(client, property_id, start, end):
    return client.post(
        BLOCKS,
        {"property": property_id, "start_date": iso(start), "end_date": iso(end)},
        format="json",
    )


@pytest.mark.parametrize(
    "method, path",
    [
        ("post", PROPERTIES),
        ("post", BOOKINGS),
        ("get", BOOKINGS),
        ("post", BLOCKS),
        ("get", BLOCKS),
    ],
)
def test_endpoints_require_api_key(db, method, path):
    resp = getattr(APIClient(), method)(path)
    assert resp.status_code == 403


def test_create_and_get_property(auth_client):
    resp = auth_client.post(PROPERTIES, {"name": "Cabin", "country_code": "CA"}, format="json")
    assert resp.status_code == 201
    pid = resp.json()["id"]
    got = auth_client.get(f"{PROPERTIES}{pid}/")
    assert got.status_code == 200
    assert got.json() == {"id": pid, "name": "Cabin", "country_code": "CA"}


def test_get_missing_property_404(auth_client):
    assert auth_client.get(f"{PROPERTIES}9999/").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"country_code": "US"},                 # missing name
        {"name": "X"},                          # missing country
        {"name": "X", "country_code": "ZZ"},    # not a real code
        {"name": "X", "country_code": "us"},    # not uppercase
        {"name": "", "country_code": "US"},     # blank name
    ],
)
def test_create_property_invalid_400(auth_client, payload):
    resp = auth_client.post(PROPERTIES, payload, format="json")
    assert resp.status_code == 400
    assert set(resp.json()) == {"error", "details"}


@given(code=st.text(max_size=5))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None, max_examples=60)
def test_create_property_country_code_fuzz(auth_client, code):
    resp = auth_client.post(PROPERTIES, {"name": "X", "country_code": code}, format="json")
    expected = 201 if code in ISO_3166_1_ALPHA2 else 400
    assert resp.status_code == expected


def test_create_booking_happy(auth_client, property_id):
    resp = book(auth_client, property_id, 10, 15)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "CONFIRMED"
    assert body["property"] == property_id


@pytest.mark.parametrize(
    "new_range, expected",
    [
        ((5, 9), 201),    # before, no touch
        ((16, 20), 201),  # after, no touch
        ((12, 14), 409),  # inside
        ((5, 10), 409),   # touches start boundary
        ((15, 20), 409),  # touches end boundary
        ((8, 18), 409),   # contains
        ((10, 15), 409),  # identical
    ],
)
def test_booking_overlap_boundaries(auth_client, property_id, new_range, expected):
    assert book(auth_client, property_id, 10, 15).status_code == 201
    resp = book(auth_client, property_id, *new_range)
    assert resp.status_code == expected
    if expected == 409:
        assert resp.json()["error"] == "conflict"


def test_create_booking_missing_property_404(auth_client):
    assert book(auth_client, 9999, 10, 15).status_code == 404


def test_create_booking_bad_dates_400(auth_client, property_id):
    assert book(auth_client, property_id, 15, 10).status_code == 400


@given(s=st.integers(min_value=1, max_value=28), e=st.integers(min_value=1, max_value=28))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None, max_examples=75)
def test_booking_overlap_matches_predicate(auth_client, s, e):
    # Fresh property per example keeps each case isolated (overlap is per-property).
    pid = auth_client.post(
        PROPERTIES, {"name": "P", "country_code": "US"}, format="json"
    ).json()["id"]
    assert book(auth_client, pid, 10, 15).status_code == 201

    resp = book(auth_client, pid, s, e)
    if s >= e:
        assert resp.status_code == 400
    elif ranges_overlap(date(2026, 1, s), date(2026, 1, e), date(2026, 1, 10), date(2026, 1, 15)):
        assert resp.status_code == 409
    else:
        assert resp.status_code == 201


def test_get_and_list_bookings(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    assert auth_client.get(f"{BOOKINGS}{bid}/").status_code == 200
    listing = auth_client.get(BOOKINGS).json()
    assert set(listing) == {"count", "next", "previous", "results"}
    assert listing["count"] == 1


def test_get_missing_booking_404(auth_client):
    assert auth_client.get(f"{BOOKINGS}9999/").status_code == 404


def test_update_booking_guest_only(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    resp = auth_client.patch(f"{BOOKINGS}{bid}/", {"guest_name": "Grace"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["guest_name"] == "Grace"


def test_update_booking_dates(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    resp = auth_client.patch(
        f"{BOOKINGS}{bid}/",
        {"start_date": iso(11), "end_date": iso(16)},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["end_date"] == iso(16)


def test_update_booking_single_date_400(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    resp = auth_client.patch(f"{BOOKINGS}{bid}/", {"start_date": iso(11)}, format="json")
    assert resp.status_code == 400


def test_update_booking_into_overlap_409(auth_client, property_id):
    book(auth_client, property_id, 20, 25)
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    resp = auth_client.patch(
        f"{BOOKINGS}{bid}/",
        {"start_date": iso(18), "end_date": iso(22)},
        format="json",
    )
    assert resp.status_code == 409


def test_cancel_frees_dates_then_rebook_conflicts(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]

    cancelled = auth_client.post(f"{BOOKINGS}{bid}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELED"

    # Dates are free now: a new booking on the same range succeeds.
    assert book(auth_client, property_id, 10, 15).status_code == 201

    # Rebooking the cancelled one now conflicts with that new booking.
    resp = auth_client.post(f"{BOOKINGS}{bid}/rebook/")
    assert resp.status_code == 409


def test_rebook_success(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    auth_client.post(f"{BOOKINGS}{bid}/cancel/")
    resp = auth_client.post(f"{BOOKINGS}{bid}/rebook/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"


def test_delete_booking(auth_client, property_id):
    bid = book(auth_client, property_id, 10, 15).json()["id"]
    assert auth_client.delete(f"{BOOKINGS}{bid}/").status_code == 204
    assert auth_client.get(f"{BOOKINGS}{bid}/").status_code == 404


def test_create_list_update_delete_block(auth_client, property_id):
    created = block(auth_client, property_id, 1, 5)
    assert created.status_code == 201
    blk = created.json()["id"]

    listing = auth_client.get(BLOCKS).json()
    assert listing["count"] == 1

    updated = auth_client.put(
        f"{BLOCKS}{blk}/", {"start_date": iso(1), "end_date": iso(6)}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["end_date"] == iso(6)

    assert auth_client.delete(f"{BLOCKS}{blk}/").status_code == 204


def test_block_over_booking_409(auth_client, property_id):
    book(auth_client, property_id, 10, 15)
    assert block(auth_client, property_id, 11, 12).status_code == 409


def test_block_over_block_409(auth_client, property_id):
    block(auth_client, property_id, 10, 15)
    assert block(auth_client, property_id, 15, 18).status_code == 409


def test_booking_over_block_409(auth_client, property_id):
    block(auth_client, property_id, 10, 15)
    assert book(auth_client, property_id, 12, 14).status_code == 409
