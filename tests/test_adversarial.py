import pytest
from rest_framework.test import APIClient

PROPERTIES = "/api/v1/properties/"
BOOKINGS = "/api/v1/bookings/"
BLOCKS = "/api/v1/blocks/"


def book(client, pid, start, end, **extra):
    payload = {"property": pid, "guest_name": "Ada", "start_date": start, "end_date": end}
    payload.update(extra)
    return client.post(BOOKINGS, payload, format="json")


def test_status_cannot_be_injected_on_create(auth_client, property_id):
    resp = book(auth_client, property_id, "2026-01-10", "2026-01-15", status="CANCELED")
    assert resp.status_code == 201
    assert resp.json()["status"] == "CONFIRMED"


def test_property_cannot_be_reassigned_on_update(auth_client, property_id):
    other = auth_client.post(
        PROPERTIES, {"name": "Other", "country_code": "CA"}, format="json"
    ).json()["id"]
    bid = book(auth_client, property_id, "2026-01-10", "2026-01-15").json()["id"]

    auth_client.patch(f"{BOOKINGS}{bid}/", {"property": other}, format="json")
    assert auth_client.get(f"{BOOKINGS}{bid}/").json()["property"] == property_id


def test_sql_injection_in_guest_name_is_stored_literally(auth_client, property_id):
    payload = "Robert'); DROP TABLE reservations_booking;--"
    resp = book(auth_client, property_id, "2026-01-10", "2026-01-15", guest_name=payload)
    assert resp.status_code == 201
    assert resp.json()["guest_name"] == payload
    # Table still intact and queryable.
    listing = auth_client.get(BOOKINGS).json()
    assert listing["count"] == 1


def test_overlap_cannot_be_bypassed_via_cancel_update_rebook(auth_client, property_id):
    a = book(auth_client, property_id, "2026-01-10", "2026-01-15").json()["id"]
    auth_client.post(f"{BOOKINGS}{a}/cancel/")

    # With A cancelled, B takes overlapping dates.
    assert book(auth_client, property_id, "2026-01-12", "2026-01-14").status_code == 201

    # Reviving A must be refused, leaving it CANCELED.
    assert auth_client.post(f"{BOOKINGS}{a}/rebook/").status_code == 409

    confirmed = [
        b for b in auth_client.get(BOOKINGS).json()["results"]
        if b["status"] == "CONFIRMED"
    ]
    assert len(confirmed) == 1


@pytest.mark.parametrize(
    "bad_dates",
    [
        ("2026-02-30", "2026-03-01"),  # day 30 of February
        ("2026-13-01", "2026-13-02"),  # month 13
        ("not-a-date", "2026-01-10"),  # garbage
        ("2026-01-10", "2026-01-10"),  # equal (must be strictly before)
    ],
)
def test_malformed_or_equal_dates_rejected(auth_client, property_id, bad_dates):
    resp = book(auth_client, property_id, *bad_dates)
    assert resp.status_code == 400
    assert set(resp.json()) == {"error", "details"}


@pytest.mark.parametrize("bad_property", [0, -1, "abc", None, [1], 1.5])
def test_non_positive_or_wrong_type_property_rejected(auth_client, bad_property):
    resp = auth_client.post(
        BOOKINGS,
        {"property": bad_property, "guest_name": "Ada",
         "start_date": "2026-01-10", "end_date": "2026-01-15"},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "method, path",
    [
        ("put", f"{PROPERTIES}1/"),
        ("delete", f"{PROPERTIES}1/"),
        ("get", f"{BLOCKS}1/"),
    ],
)
def test_unsupported_methods_405(auth_client, property_id, method, path):
    assert getattr(auth_client, method)(path).status_code == 405


@pytest.mark.parametrize(
    "header",
    ["Bearer sometoken", "Api-Key", "Api-Key ", "Api-Key wrong-key", "garbage"],
)
def test_malformed_auth_header_rejected(db, header):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=header)
    assert client.get(BOOKINGS).status_code == 403


def test_malformed_json_body_400(auth_client):
    resp = auth_client.post(BOOKINGS, data="{not valid json", content_type="application/json")
    assert resp.status_code == 400
    assert set(resp.json()) == {"error", "details"}


def test_oversized_guest_name_400(auth_client, property_id):
    resp = book(auth_client, property_id, "2026-01-10", "2026-01-15", guest_name="x" * 1000)
    assert resp.status_code == 400
