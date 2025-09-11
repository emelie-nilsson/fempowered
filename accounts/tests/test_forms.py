from django.test import TestCase
from accounts.forms import UserAddressForm


class UserAddressFormTests(TestCase):
    def valid_data(self):
        """Baseline valid shipping-only address (SE)."""
        return {
            "full_name": "Emelie Nilsson",
            "email": "emelie@example.com",
            "phone": "+46 70 123 45 67",
            "address1": "Baker Street 1",
            "address2": "",
            "postal_code": "21145",  # SE: exactly 5 digits
            "city": "Malmö",
            "country": "SE",         # ISO code (max_length=2)
            "billing_same_as_shipping": True,  # billing not required when True
            "billing_address1": "",
            "billing_address2": "",
            "billing_postal_code": "",
            "billing_city": "",
            "billing_country": "",
        }

    # ---- happy path ----
    def test_valid_form_passes(self):
        form = UserAddressForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    # negative: name 
    def test_full_name_requires_two_parts(self):
        data = self.valid_data()
        data["full_name"] = "Emelie"
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

    # negative: phone 
    def test_phone_requires_7_to_15_digits(self):
        data = self.valid_data()
        data["phone"] = "12-34-56"  # only 6 digits
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    # country-specific: SE 
    def test_sweden_postcode_requires_5_digits(self):
        data = self.valid_data()
        data["country"] = "SE"
        data["postal_code"] = "123"  # too short
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("postal_code", form.errors)

    # country-specific: UK/GB 
    def test_uk_postcode_valid_and_normalizes(self):
        data = self.valid_data()
        data["country"] = "GB"
        data["postal_code"] = "SW1A1AA"  # will normalize to "SW1A 1AA"
        form = UserAddressForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())
        self.assertEqual(form.cleaned_data["postal_code"], "SW1A 1AA")

    def test_uk_postcode_invalid_format(self):
        data = self.valid_data()
        data["country"] = "GB"
        data["postal_code"] = "12345"  # invalid for UK
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("postal_code", form.errors)

    #  billing rules 
    def test_billing_fields_required_when_not_same(self):
        data = self.valid_data()
        data["billing_same_as_shipping"] = False
        # leave billing fields empty
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        for field in ["billing_address1", "billing_postal_code", "billing_city", "billing_country"]:
            self.assertIn(field, form.errors, msg=f"Expected error on {field}")

    def test_billing_fields_ok_when_provided_and_not_same(self):
        data = self.valid_data()
        data["billing_same_as_shipping"] = False
        data["billing_address1"] = "Billinggatan 2"
        data["billing_postal_code"] = "EC1A1BB"  # UK style — will be normalized if country=GB
        data["billing_city"] = "London"
        data["billing_country"] = "GB"
        form = UserAddressForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())
        self.assertEqual(form.cleaned_data["billing_postal_code"], "EC1A 1BB")
