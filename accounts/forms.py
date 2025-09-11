from django import forms
from django.core.exceptions import ValidationError
import re
from .models import UserAddress


# ---------------------------
# Validators (reusable)
# ---------------------------

def validate_full_name(value: str) -> None:
    """
    Require at least two name parts (first + last).
    Allow letters (incl. accents), spaces, hyphens, apostrophes.
    """
    parts = [p for p in (value or "").strip().split() if p]
    if len(parts) < 2:
        raise ValidationError("Please enter both first and last name.")
    for p in parts:
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,}", p):
            raise ValidationError("Name may only contain letters, spaces, hyphens and apostrophes.")


def validate_phone(value: str) -> None:
    """
    Require 7–15 digits overall.
    Allow +, spaces, hyphens, dots and parentheses as formatting.
    """
    v = (value or "").strip()
    digits = re.sub(r"\D", "", v)
    if not (7 <= len(digits) <= 15):
        raise ValidationError("Enter a valid phone number (7–15 digits).")
    if not re.fullmatch(r"^\+?[0-9\s().-]+$", v):
        raise ValidationError("Phone may only contain digits, spaces, +, -, and parentheses.")


def validate_postcode_generic(raw: str) -> None:
    """
    Fallback for countries without a specific rule:
    accept 3–10 digits in total (lenient, international-friendly).
    """
    digits = re.sub(r"\D", "", raw or "")
    if not (3 <= len(digits) <= 10):
        raise ValidationError("Postal code should be 3–10 digits.")


def validate_postcode_by_country(value: str, country: str) -> str:
    """
    Country-specific postal code validation.
    Returns a normalized postal code string where applicable.
    - SE: exactly 5 digits (e.g., '21145'). Input like '211 45' is normalized to '21145'.
    - GB/UK: UK postcode; normalizes spacing to 'OUTCODE INCODE' (space before last 3 chars).
    - Fallback: 3–10 digits (keeps original formatting).
    """
    country = (country or "").upper().strip()
    raw = (value or "").strip()

    # Sweden: 5 digits
    if country == "SE":
        digits = re.sub(r"\D", "", raw)
        if not re.fullmatch(r"\d{5}", digits):
            raise ValidationError("Swedish postal code must be exactly 5 digits (e.g., 21145).")
        return digits  # normalized

    # United Kingdom: UK postcodes (various formats). Normalize and validate with regex.
    if country in ("GB", "UK"):
        compact = raw.upper().replace(" ", "")
        normalized = compact[:-3] + " " + compact[-3:] if len(compact) > 3 else compact

        uk_pattern = re.compile(
            r"^([Gg][Ii][Rr] 0[Aa]{2})|"  # GIR 0AA (special)
            r"((([A-Za-z][0-9]{1,2})|"    # A9 / A99
            r"(([A-Za-z][A-HJ-Ya-hj-y][0-9]{1,2})|"  # AA9 / AA99
            r"(([A-Za-z][0-9][A-Za-z])|"  # A9A
            r"([A-Za-z][A-HJ-Ya-hj-y][0-9]?[A-Za-z]?))))"  # AA9A / AA9
            r"\s?[0-9][A-Za-z]{2})$"      # space (optional) + 9AA
        )
        if not uk_pattern.match(normalized):
            raise ValidationError("Enter a valid UK postcode (e.g., SW1A 1AA).")
        return normalized

    # Fallback: lenient numeric length check
    validate_postcode_generic(raw)
    return raw


# ---------------------------
# Form
# ---------------------------

class UserAddressForm(forms.ModelForm):
    """
    ModelForm for UserAddress.
    - Field-level validation for full_name, phone, and (billing_)postal_code.
    - Country-specific postal code rules (SE, GB/UK), with a generic fallback.
    - Enforces billing fields when billing_same_as_shipping is False.
    """

    class Meta:
        model = UserAddress
        fields = [
            "full_name", "email", "phone",
            "address1", "address2",
            "country",        # <- moved before postal_code
            "postal_code",
            "city",
            "billing_same_as_shipping",
            "billing_address1", "billing_address2",
            "billing_country",    # <- moved before billing_postal_code
            "billing_postal_code",
            "billing_city",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First and last name", "required": True}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com", "required": True}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+46 70 123 45 67", "inputmode": "tel", "required": True}),
            "address1": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "address2": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control", "placeholder": "SE / GB", "required": True}),
            "postal_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., 21145 / SW1A 1AA", "required": True}),
            "city": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "billing_same_as_shipping": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "billing_address1": forms.TextInput(attrs={"class": "form-control"}),
            "billing_address2": forms.TextInput(attrs={"class": "form-control"}),
            "billing_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "SE / GB"}),
            "billing_postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "billing_city": forms.TextInput(attrs={"class": "form-control"}),
        }

    # -------- field-level clean_* --------

    def _get_country_value(self) -> str:
        """
        Robustly obtain shipping country, even if field cleaning order changes.
        """
        return (self.cleaned_data.get("country")
                or self.data.get(self.add_prefix("country"))
                or "").strip()

    def _get_billing_country_value(self) -> str:
        """
        Robustly obtain billing country, even if field cleaning order changes.
        """
        return (self.cleaned_data.get("billing_country")
                or self.data.get(self.add_prefix("billing_country"))
                or "").strip()

    def clean_full_name(self):
        v = (self.cleaned_data.get("full_name") or "").strip()
        validate_full_name(v)
        return " ".join(v.split())

    def clean_phone(self):
        v = (self.cleaned_data.get("phone") or "").strip()
        validate_phone(v)
        return v

    def clean_postal_code(self):
        code = (self.cleaned_data.get("postal_code") or "").strip()
        country = self._get_country_value()
        return validate_postcode_by_country(code, country)

    def clean_billing_postal_code(self):
        code = (self.cleaned_data.get("billing_postal_code") or "").strip()
        if not code:
            return code  # requiredness handled in form-level clean()
        country = self._get_billing_country_value()
        return validate_postcode_by_country(code, country)

    # -------- form-level clean() --------

    def clean(self):
        """
        When billing_same_as_shipping is False, require billing fields.
        Attach errors to specific fields (no non-field error noise).
        """
        cleaned = super().clean()
        same = cleaned.get("billing_same_as_shipping", True)

        if not same:
            required_billing = {
                "billing_address1": "Billing address is required.",
                "billing_postal_code": "Billing postal code is required.",
                "billing_city": "Billing city is required.",
                "billing_country": "Billing country is required.",
            }
            for field, msg in required_billing.items():
                val = (cleaned.get(field) or "").strip()
                if not val:
                    self.add_error(field, msg)

        return cleaned
