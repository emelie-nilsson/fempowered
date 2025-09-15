import re
from django.core.exceptions import ValidationError


def validate_full_name(value: str) -> None:
    # First and lastname minimum
    parts = [p for p in value.strip().split() if p]
    if len(parts) < 2:
        raise ValidationError("Please enter both first and last name.")
    for p in parts:
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,}", p):
            raise ValidationError("Name may only contain letters, spaces, hyphens and apostrophes.")


def validate_phone(value: str) -> None:
    digits = re.sub(r"\D", "", value)
    if not (7 <= len(digits) <= 15):
        raise ValidationError("Enter a valid phone number (7–15 digits).")
    # Allow +, space, -, ()
    if not re.fullmatch(r"^\+?[0-9\s().-]+$", value):
        raise ValidationError("Phone may only contain digits, spaces, +, -, and parentheses.")


def validate_postcode(value: str) -> None:
    digits = re.sub(r"\D", "", value)
    if not (3 <= len(digits) <= 10):
        raise ValidationError("Postal code should be 3–10 digits.")
