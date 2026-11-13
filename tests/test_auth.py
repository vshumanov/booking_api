import pytest
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def api_key(db):
    _, key = APIKey.objects.create_key(name="test-client")
    return key


def auth(key):
    return {"HTTP_AUTHORIZATION": f"Api-Key {key}"}


def test_api_requires_key(client, db):
    assert client.get("/api/v1/").status_code == 403


def test_api_accepts_valid_key(client, api_key):
    assert client.get("/api/v1/", **auth(api_key)).status_code == 200


def test_api_rejects_invalid_key(client, db):
    assert client.get("/api/v1/", **auth("not-a-real-key")).status_code == 403


def test_api_rejects_revoked_key(client, db):
    obj, key = APIKey.objects.create_key(name="revoked-client")
    obj.revoked = True
    obj.save()
    assert client.get("/api/v1/", **auth(key)).status_code == 403


def test_error_body_is_structured_on_403(client, db):
    body = client.get("/api/v1/").json()
    assert set(body) == {"error", "details"}
    assert body["error"] == "forbidden"


def test_docs_open_without_key(client, db):
    assert client.get("/api/docs/").status_code == 200
    assert client.get("/api/schema/").status_code == 200
