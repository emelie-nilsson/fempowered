from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class CheckoutSuccessViewSmokeTests(TestCase):
    """
    Smoke tests for checkout success/confirmation page.
    Accept typical statuses; allow 404/400 if an order id is required.
    """

    OK = (200, 302, 303, 400, 403)
    OK_OR_404 = (200, 302, 303, 400, 403, 404)

    def _reverse_first(self, candidates):
        for name, kwargs in candidates:
            try:
                return reverse(name, kwargs=kwargs or None), name
            except NoReverseMatch:
                continue
        return None, None

    def test_success_page_without_id(self):
        url, name = self._reverse_first([
            ("checkout:success", None),
            ("checkout_success", None),
            ("checkout:confirmation", None),
            ("checkout_confirmation", None),
        ])
        if not url:
            self.skipTest("No reverseable URL for success page without id")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK, f"{name} unexpected {resp.status_code} at {url}")

    def test_success_page_with_dummy_id(self):
        url, name = self._reverse_first([
            ("checkout:success", {"order_id": "TEST123"}),
            ("checkout_success", {"order_id": "TEST123"}),
            ("checkout:confirmation", {"order_id": "TEST123"}),
            ("checkout_confirmation", {"order_id": "TEST123"}),
        ])
        if not url:
            self.skipTest("No reverseable URL for success page with order_id")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK_OR_404, f"{name} unexpected {resp.status_code} at {url}")
