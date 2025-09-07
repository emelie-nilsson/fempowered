from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ProductListSmokeTests(TestCase):
    """
    Smoke tests for product listing/search/filter endpoint(s).
    Ensures page exists and doesn't 500 with simple query params.
    """

    OK = (200, 302, 303, 400, 403)

    def _reverse_first(self, names):
        for n in names:
            try:
                return reverse(n), n
            except NoReverseMatch:
                continue
        return None, None

    def test_product_list_base(self):
        url, name = self._reverse_first(("shop:product_list", "product_list", "shop:index", "shop_home"))
        if not url:
            self.skipTest("No reverseable URL for product list")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK, f"{name} unexpected {resp.status_code} at {url}")

    def test_product_list_with_search_query(self):
        url, name = self._reverse_first(("shop:product_list", "product_list"))
        if not url:
            self.skipTest("No reverseable URL for product list with query")
            return
        resp = self.client.get(url, {"q": "test"})
        self.assertIn(resp.status_code, self.OK, f"{name} with ?q= unexpected {resp.status_code} at {url}")

    def test_product_list_with_category_filter(self):
        url, name = self._reverse_first(("shop:product_list", "product_list"))
        if not url:
            self.skipTest("No reverseable URL for product list with category")
            return
        # Use a dummy slug; page should still handle gracefully.
        resp = self.client.get(url, {"category": "non-existent"})
        self.assertIn(resp.status_code, self.OK, f"{name} with ?category= unexpected {resp.status_code} at {url}")
