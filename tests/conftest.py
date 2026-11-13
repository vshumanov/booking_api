import pytest
from rest_framework.test import APIClient
from rest_framework_api_key.models import APIKey


@pytest.fixture
def auth_client(db):
    client = APIClient()
    _, key = APIKey.objects.create_key(name="tests")
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {key}")
    return client


@pytest.fixture
def property_id(auth_client):
    resp = auth_client.post(
        "/api/v1/properties/",
        {"name": "Beach House", "country_code": "US"},
        format="json",
    )
    assert resp.status_code == 201
    return resp.json()["id"]
