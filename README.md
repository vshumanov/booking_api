# Booking Service

A small REST API for managing property **bookings** and **blocks**, with inclusive date-overlap prevention. Built with Django REST Framework, SQLite, and `uv`, and runs as a Docker container.

## Description

Three resources under `/api/v1/`, all requiring an API key (`Authorization: Api-Key <key>`):

- **Properties** — create, retrieve.
- **Bookings** — create, retrieve, list, update (dates/guest), cancel, rebook, delete.
- **Blocks** — create, update, delete, list.

A booking or block cannot share a single day with any non-canceled booking or block on the same property. The check runs on create, update, and rebook. Overlap conflicts return `409`; validation errors `400`; unknown references `404`; every error uses a consistent `{"error": ..., "details": ...}` body.

Interactive API docs (OpenAPI/Swagger) are served at `/api/docs/`.

## Deployment

```bash
docker compose up --build
```

Then seed sample data and get an API key:

```bash
docker compose exec web uv run python manage.py seed
```

The service listens on `http://localhost:8000`. Docs: `http://localhost:8000/api/docs/`.

Local development (without Docker):

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed
uv run python manage.py runserver
uv run pytest
```

## Design Notes

**Framework & database.** Django REST Framework gives us ViewSets, serializers, routing, auth, and pagination out of the box, so the effort goes into the overlap domain rather than HTTP plumbing. Business logic lives in a `services.py` layer; serializers stay thin and ViewSets just delegate. SQLite (through the ORM) keeps the project dependency-free to run while still exercising a real database/migration layer.

**Overlap check.** Two inclusive date ranges overlap when `start_a <= end_b and start_b <= end_a`. The pure predicate is unit-tested against the spec's boundary table; the service applies it as a DB query filtered by property (and, for bookings, `status=CONFIRMED`), excluding the row being updated. Each mutating operation runs in a transaction that locks the parent property (`select_for_update`) before checking and writing, so two concurrent requests for the same property are serialized.

**Trade-offs / limitations.**

- **`409 Conflict`** for overlaps — a conflict with existing state, not a malformed request.
- **Inclusive boundaries** (per the spec) mean a range ending on a day and another starting that same day overlap — so there's no same-day turnover and the minimum booking is two calendar days.
- **Blocks are overlap-checked too**, against bookings and other blocks. The spec only required this for bookings; extending it to blocks keeps a property's calendar internally consistent.
- **Rebook restores the original dates** and re-runs the overlap check; rescheduling is a separate `update` call.
- **`country_code` is strict ISO 3166-1 alpha-2**, uppercase only (lowercase is rejected, not coerced).
- Dates are **timezone-independent calendar days**, and **past-dated bookings are allowed** (no "today" check, which would introduce a server-timezone dependency).
- **Concurrency:** `select_for_update` is a no-op on SQLite, but SQLite's database-level write lock serializes writers all the same — a true concurrency test would need Postgres.
- **No rate limiting** — would need DRF throttling plus a shared cache (e.g. Redis) for multi-worker deployments.
- **Sequential integer IDs are enumerable** — harmless under the single full-access API key (the `list` endpoints already return everything), but a multi-tenant or publicly-exposed deployment should move to UUID/opaque IDs and add per-object authorization.
