from django.test import SimpleTestCase
from checkout.forms import CheckoutAddressForm
from checkout.models import ShippingMethod


class CheckoutAddressFormTests(SimpleTestCase):
    def valid_payload(self, **overrides):
        data = {
            "full_name": "Anna Andersson",
            "email": "anna@example.com",
            "phone": "+46 70-123 45 67",
            "address1": "Test Street 1",
            "address2": "",
            "postal_code": "12345",
            "city": "Stockholm",
            "country": "SE",
            "shipping_method": ShippingMethod.STANDARD.value,
            "billing_same_as_shipping": True,
            "billing_address1": "",
            "billing_address2": "",
            "billing_postal_code": "",
            "billing_city": "",
            "billing_country": "",
        }
        data.update(overrides)
        return data

    def test_valid_form_passes(self):
        form = CheckoutAddressForm(data=self.valid_payload())
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_phone_too_short_is_invalid(self):
        form = CheckoutAddressForm(data=self.valid_payload(phone="123"))
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_postal_code_must_be_digits(self):
        form = CheckoutAddressForm(data=self.valid_payload(postal_code="AB12"))
        self.assertFalse(form.is_valid())
        self.assertIn("postal_code", form.errors)

    def test_full_name_requires_first_and_last(self):
        form = CheckoutAddressForm(data=self.valid_payload(full_name="Anna"))
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

    def test_billing_required_when_not_same_as_shipping(self):
        form = CheckoutAddressForm(
            data=self.valid_payload(
                billing_same_as_shipping=False,
                billing_address1="",
                billing_postal_code="",
                billing_city="",
                billing_country="",
            )
        )
        self.assertFalse(form.is_valid())
        for field in ("billing_address1", "billing_postal_code", "billing_city", "billing_country"):
            self.assertIn(field, form.errors)
