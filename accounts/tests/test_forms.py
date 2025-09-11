from django.test import TestCase
from accounts.forms import UserAddressForm


class UserAddressFormTests(TestCase):
    def valid_data(self):
        # Matches UserAddressForm fields exactly
        return {
            "full_name": "Emelie Nilsson",
            "email": "emelie@example.com",
            "phone": "+46 70 123 45 67",
            "address1": "Baker Street 1",
            "address2": "",
            "postal_code": "21145",
            "city": "Malmö",
            "country": "SE",
            "billing_same_as_shipping": True,  # billing fields not required when True
            "billing_address1": "",
            "billing_address2": "",
            "billing_postal_code": "",
            "billing_city": "",
            "billing_country": "",
        }

    def test_valid_form_passes(self):
        form = UserAddressForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())

    def test_full_name_requires_two_parts(self):
        data = self.valid_data()
        data["full_name"] = "Emelie"
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)

    def test_phone_requires_7_to_15_digits(self):
        data = self.valid_data()
        data["phone"] = "12-34-56"  # only 6 digits
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_postal_code_must_be_3_to_10_digits(self):
        data = self.valid_data()
        data["postal_code"] = "12"  # too short
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("postal_code", form.errors)

    def test_billing_fields_required_when_not_same(self):
        data = self.valid_data()
        data["billing_same_as_shipping"] = False
        # leave all billing fields empty
        form = UserAddressForm(data=data)
        self.assertFalse(form.is_valid())
        for field in ["billing_address1", "billing_postal_code", "billing_city", "billing_country"]:
            self.assertIn(field, form.errors, msg=f"Expected error on {field}")

    def test_billing_fields_ok_when_provided_and_not_same(self):
        data = self.valid_data()
        data["billing_same_as_shipping"] = False
        data["billing_address1"] = "Billinggatan 2"
        data["billing_postal_code"] = "12345"
        data["billing_city"] = "Lund"
        data["billing_country"] = "SE"
        form = UserAddressForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_json())
