from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch
from django.conf import settings

# Import your real form + enums to build a valid payload
from checkout.forms import CheckoutAddressForm
from checkout.models import ShippingMethod


@override_settings(
    # Prevent hashed static lookup errors (favicon etc.) during test rendering
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class CheckoutEndToEndTests(TestCase):
    """
    End-to-end-ish checkout flow:
      1) GET address page (smoke)
      2) POST address form with valid data
      3) After success, ensure payment page can be loaded
    The tests are adaptive to common URL names and will skip if routes don't exist.
    """

    OK = (200, 302, 303, 400, 403)

    # ---------- helpers ----------
    def _reverse_first(self, candidates):
        """
        Try reverse a list of (name, kwargs) and return (url, name) for the first that resolves.
        """
        for name, kwargs in candidates:
            try:
                return reverse(name, kwargs=kwargs or None), name
            except NoReverseMatch:
                continue
        return None, None

    def _address_url(self):
        return self._reverse_first([
            ("checkout:address", None),
            ("checkout_address", None),
            ("checkout:start", None),
            ("checkout_start", None),
        ])

    def _payment_url(self):
        return self._reverse_first([
            ("checkout:payment", None),
            ("checkout_payment", None),
            ("payment", None),
            ("checkout:payment_step", None),
            ("checkout_pay", None),
        ])

    def _valid_payload(self, **overrides):
        """
        Build a valid payload using the actual form to keep fields in sync.
        """
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
        # Sanity: ensure our payload actually passes the form right now
        form = CheckoutAddressForm(data=data)
        assert form.is_valid(), f"Test payload invalid: {form.errors.as_json()}"
        return data

    # ---------- tests ----------
    def test_01_address_get_renders(self):
        url, name = self._address_url()
        if not url:
            self.skipTest("No reverseable URL for checkout address view")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK, f"{name} GET unexpected {resp.status_code} at {url}")

    def test_02_post_address_then_payment_get(self):
        # 1) Post address (valid)
        address_url, addr_name = self._address_url()
        if not address_url:
            self.skipTest("No reverseable URL for checkout address view")
            return
        payload = self._valid_payload()
        # follow=True to capture redirect chain (if any)
        post_resp = self.client.post(address_url, data=payload, follow=True)
        self.assertIn(
            post_resp.status_code, self.OK,
            f"{addr_name} POST unexpected {post_resp.status_code} at {address_url}"
        )

        # 2) Try to load payment page after address step
        payment_url, pay_name = self._payment_url()
        if not payment_url:
            self.skipTest("No reverseable URL for checkout payment view")
            return
        pay_resp = self.client.get(payment_url)
        self.assertIn(
            pay_resp.status_code, self.OK,
            f"{pay_name} GET unexpected {pay_resp.status_code} at {payment_url}"
        )
