from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class CheckoutPaymentViewsSmokeTests(TestCase):
    """
    Smoke tests for the checkout payment step.
    Goal: ensure pages respond without server errors on GET/POST.
    Adaptive and will skip if no matching URL names exist.
    """

    OK_GET = (200, 302, 303, 400, 403)
    OK_POST = (200, 302, 303, 400, 403, 405)  # 405 allowed if view is GET-only

    def _reverse_or_none(self, name):
        try:
            return reverse(name)
        except NoReverseMatch:
            return None

    def _find_payment_url(self):
        for name in (
            "checkout:payment",
            "checkout_payment",
            "payment",
            "checkout:payment_step",
            "checkout:pay",
            "checkout_pay",
        ):
            url = self._reverse_or_none(name)
            if url:
                return url, name
        return None, None

    def test_payment_get_does_not_crash(self):
        url, name = self._find_payment_url()
        if not url:
            self.skipTest("No reverseable URL found for checkout payment view")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK_GET, f"{name} unexpected {resp.status_code} at {url}")

    def test_payment_post_does_not_crash(self):
        url, name = self._find_payment_url()
        if not url:
            self.skipTest("No reverseable URL found for checkout payment view")
            return
        resp = self.client.post(url, data={"nonce": "test", "agree_terms": "on"})
        self.assertIn(resp.status_code, self.OK_POST, f"{name} POST unexpected {resp.status_code} at {url}")
