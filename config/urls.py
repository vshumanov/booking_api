"""Root URL configuration.

The API is versioned via the URL path: every resource lives under
`/api/<version>/` (currently `v1`). OpenAPI schema and Swagger UI are served
outside the versioned prefix and are intentionally left open so the API can be
explored without a key.
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny


class _OpenSchemaView(SpectacularAPIView):
    permission_classes = [AllowAny]


class _OpenSwaggerView(SpectacularSwaggerView):
    permission_classes = [AllowAny]


urlpatterns = [
    # API documentation (open, no key required). Declared before the versioned
    # catch-all so the `<version>` converter doesn't capture "schema"/"docs".
    path("api/schema/", _OpenSchemaView.as_view(), name="schema"),
    path("api/docs/", _OpenSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/<version>/", include("reservations.urls")),
]
