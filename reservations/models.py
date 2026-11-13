from django.core.validators import RegexValidator
from django.db import models

from .validators import validate_country_code


class Property(models.Model):
    name = models.CharField(max_length=255)
    country_code = models.CharField(
        max_length=2,
        validators=[
            RegexValidator(r"^[A-Z]{2}$", "Country code must be two uppercase letters."),
            validate_country_code,
        ],
    )

    class Meta:
        verbose_name_plural = "properties"

    def __str__(self) -> str:
        return f"{self.name} ({self.country_code})"


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELED = "CANCELED", "Canceled"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    guest_name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=9,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lt=models.F("end_date")),
                name="booking_start_before_end",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "status", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"Booking #{self.pk} [{self.status}] {self.start_date}..{self.end_date}"


class Block(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lt=models.F("end_date")),
                name="block_start_before_end",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"Block #{self.pk} {self.start_date}..{self.end_date}"
