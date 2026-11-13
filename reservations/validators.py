from django.core.exceptions import ValidationError

from .countries import ISO_3166_1_ALPHA2


def validate_country_code(value: str) -> None:
    """Reject anything that is not a real ISO 3166-1 alpha-2 code (uppercase)."""
    if value not in ISO_3166_1_ALPHA2:
        raise ValidationError(
            "%(value)s is not a valid ISO 3166-1 alpha-2 country code.",
            params={"value": value},
        )
