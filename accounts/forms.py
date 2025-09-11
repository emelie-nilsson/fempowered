from django import forms
from django.core.exceptions import ValidationError
import re
from .models import UserAddress


# Custom validators

def validate_full_name(value: str) -> None:
    """
    Ensure the full name contains at least two parts (first and last name).
    Only letters, spaces, hyphens, and apostrophes are allowed.
    """
    parts = [p for p in value.strip().split() if p]
    if len(parts) < 2:
        raise ValidationError("Please enter both first and last name.")
    for p in parts:
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,}", p):
            raise ValidationError(
                "Name may only contain letters, spaces, hyphens and apostrophes."
            )


def validate_phone(value: str) -> None:
    """
    Ensure phone number has 7–15 digits.
    Allow +, spaces, hyphens, dots, and parentheses.
    """
    digits = re.sub(r"\D", "", value)
    if not (7 <= len(digits) <= 15):
        raise ValidationError("Enter a valid phone number (7–15 digits).")
    if not re.fullmatch(r"^\+?[0-9\s().-]+$", value):
        raise ValidationError("Phone may only contain digits, spaces, +, -, and parentheses.")


def validate_postcode(value: str) -> None:
    """
    Ensure postal code has 3–10 digits.
    Basic numeric validation only, format can be extended per country if needed.
    """
    digits = re.sub(r"\D", "", value)
    if not (3 <= len(digits) <= 10):
        raise ValidationError("Postal code should be 3–10 digits.")


# Form class

class UserAddressForm(forms.ModelForm):
    """
    ModelForm for UserAddress model.
    Includes custom validation for full_name, phone, and postal_code fields.
    Enforces billing fields when billing_same_as_shipping is False.
    """

    class Meta:
        model = UserAddress
        fields = [
            "full_name", "email", "phone",
            "address1", "address2", "postal_code", "city", "country",
            "billing_same_as_shipping",
            "billing_address1", "billing_address2", "billing_postal_code",
            "billing_city", "billing_country",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "First and last name", "required": True}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "name@example.com", "required": True}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "+46 70 123 45 67", "inputmode": "tel", "required": True}),
            "address1": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "address2": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "12345", "inputmode": "numeric", "required": True}),
            "city": forms.TextInput(attrs={"class": "form-control", "required": True}),
            "country": forms.TextInput(attrs={"class": "form-control", "required": True, "placeholder": "SE"}),
            "billing_same_as_shipping": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "billing_address1": forms.TextInput(attrs={"class": "form-control"}),
            "billing_address2": forms.TextInput(attrs={"class": "form-control"}),
            "billing_postal_code": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric"}),
            "billing_city": forms.TextInput(attrs={"class": "form-control"}),
            "billing_country": forms.TextInput(attrs={"class": "form-control", "placeholder": "SE"}),
        }

    # Field-level validation

    def clean_full_name(self):
        """Validate full_name using custom validator."""
        value = self.cleaned_data["full_name"].strip()
        validate_full_name(value)
        return " ".join(value.split())

    def clean_phone(self):
        """Validate phone using custom validator."""
        value = self.cleaned_data["phone"].strip()
        validate_phone(value)
        return value

    def clean_postal_code(self):
        """Validate postal_code using custom validator."""
        value = self.cleaned_data["postal_code"].strip()
        validate_postcode(value)
        return value

    def clean_billing_postal_code(self):
        """
        Validate billing postal code if provided.
        Required-logic is handled in clean() depending on billing_same_as_shipping.
        """
        value = (self.cleaned_data.get("billing_postal_code") or "").strip()
        if value:
            validate_postcode(value)
        return value

    # Form-level validation

    def clean(self):
        """
        Enforce billing fields when billing_same_as_shipping is False.
        Adds errors to specific fields instead of raising a non-field error.
        """
        cleaned = super().clean()
        same = cleaned.get("billing_same_as_shipping", True)

        if not same:
            required_billing_fields = {
                "billing_address1": "Billing address is required.",
                "billing_postal_code": "Billing postal code is required.",
                "billing_city": "Billing city is required.",
                "billing_country": "Billing country is required.",
            }
            for field, msg in required_billing_fields.items():
                val = (cleaned.get(field) or "").strip()
                if not val:
                    self.add_error(field, msg)

            # If a billing postal code exists, it will be validated by clean_billing_postal_code().
            # If empty, the loop above already adds an error.

        return cleaned
