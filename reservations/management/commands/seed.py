from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework_api_key.models import APIKey

from reservations import services
from reservations.models import Block, Booking, Property


class Command(BaseCommand):
    help = "Populate the database with sample properties, bookings, and blocks for manual testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing properties, bookings, and blocks before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Booking.objects.all().delete()
            Block.objects.all().delete()
            Property.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing properties, bookings, and blocks."))

        beach = services.create_property(name="Beach House", country_code="US")
        cabin = services.create_property(name="Mountain Cabin", country_code="CA")

        services.create_booking(
            property_id=beach.id, guest_name="Ada Lovelace",
            start_date=date(2026, 1, 10), end_date=date(2026, 1, 15),
        )
        services.create_booking(
            property_id=beach.id, guest_name="Bob Martin",
            start_date=date(2026, 1, 20), end_date=date(2026, 1, 25),
        )
        canceled = services.create_booking(
            property_id=beach.id, guest_name="Carol King",
            start_date=date(2026, 2, 1), end_date=date(2026, 2, 5),
        )
        services.cancel_booking(canceled)

        services.create_block(
            property_id=beach.id,
            start_date=date(2026, 3, 1), end_date=date(2026, 3, 5),
        )

        services.create_booking(
            property_id=cabin.id, guest_name="Dave Grohl",
            start_date=date(2026, 1, 12), end_date=date(2026, 1, 18),
        )
        services.create_block(
            property_id=cabin.id,
            start_date=date(2026, 1, 25), end_date=date(2026, 1, 28),
        )

        _, key = APIKey.objects.create_key(name="seed")

        self.stdout.write(self.style.SUCCESS("Seeded sample data:"))
        self.stdout.write(f"  Property {beach.id}: Beach House (US) — 2 confirmed bookings, 1 canceled, 1 block")
        self.stdout.write(f"  Property {cabin.id}: Mountain Cabin (CA) — 1 confirmed booking, 1 block")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("API key (shown once — save it):"))
        self.stdout.write(f"  {key}")
        self.stdout.write("")
        self.stdout.write("Example request:")
        self.stdout.write(
            f'  curl -H "Authorization: Api-Key {key}" http://localhost:8000/api/v1/bookings/'
        )
