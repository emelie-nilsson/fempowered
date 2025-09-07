from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ShopCartViewsSmokeTests(TestCase):
    """
    Smoke tests for cart pages that live in the 'shop' app.
    We only assert that endpoints respond without crashing.
    """

    OK = (200, 302, 303, 400, 403)
    OK_OR_404 = (200, 302, 303, 400, 403, 404)

    def _reverse_or_none(self, name, **kwargs):
        try:
            return reverse(name, kwargs=kwargs or None)
        except NoReverseMatch:
            return None

    def test_cart_page_renders(self):
        # Common name patterns for cart page in shop app
        for name in ("shop:cart", "shop:cart_view", "cart", "cart_view"):
            url = self._reverse_or_none(name)
            if not url:
                continue
            resp = self.client.get(url)
            self.assertIn(
                resp.status_code,
                self.OK,
                f"{name} unexpected {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for cart page in shop")

    def test_add_to_cart_endpoint_does_not_crash(self):
        # Using non-existent product id; 404 is acceptable.
        candidates = [
            ("shop:cart_add", {"pk": 999999}),
            ("shop:add_to_cart", {"pk": 999999}),
            ("cart_add", {"pk": 999999}),
            ("add_to_cart", {"pk": 999999}),
            ("shop:cart_add", {"product_id": 999999}),
            ("shop:add_to_cart", {"product_id": 999999}),
            ("cart_add", {"product_id": 999999}),
            ("add_to_cart", {"product_id": 999999}),
        ]
        for name, kw in candidates:
            url = self._reverse_or_none(name, **kw)
            if not url:
                continue
            resp = self.client.post(url, data={"quantity": 1})
            self.assertIn(
                resp.status_code,
                self.OK_OR_404,
                f"{name} unexpected {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for add-to-cart in shop")

    def test_update_cart_endpoint_does_not_crash(self):
        candidates = [
            ("shop:cart_update", {"pk": 999999}),
            ("cart_update", {"pk": 999999}),
            ("shop:cart_update", {"product_id": 999999}),
            ("cart_update", {"product_id": 999999}),
        ]
        for name, kw in candidates:
            url = self._reverse_or_none(name, **kw)
            if not url:
                continue
            resp = self.client.post(url, data={"quantity": 2})
            self.assertIn(
                resp.status_code,
                self.OK_OR_404,
                f"{name} unexpected {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for update-cart in shop")

    def test_remove_from_cart_endpoint_does_not_crash(self):
        candidates = [
            ("shop:cart_remove", {"pk": 999999}),
            ("shop:remove_from_cart", {"pk": 999999}),
            ("cart_remove", {"pk": 999999}),
            ("remove_from_cart", {"pk": 999999}),
            ("shop:cart_remove", {"product_id": 999999}),
            ("shop:remove_from_cart", {"product_id": 999999}),
            ("cart_remove", {"product_id": 999999}),
            ("remove_from_cart", {"product_id": 999999}),
        ]
        for name, kw in candidates:
            url = self._reverse_or_none(name, **kw)
            if not url:
                continue
            resp = self.client.post(url)
            self.assertIn(
                resp.status_code,
                self.OK_OR_404,
                f"{name} unexpected {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for remove-from-cart in shop")
