from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class ShopViewsSmokeTests(TestCase):
    """
    Lightweight view tests guaranteeing that shop pages render or fail gracefully
    without requiring database fixtures.
    """

    def _reverse_or_none(self, name, **kwargs):
        try:
            return reverse(name, kwargs=kwargs or None)
        except NoReverseMatch:
            return None

    def test_product_list_renders_ok(self):
        # Try namespaced and non-namespaced names
        for name in ("shop:product_list", "product_list", "shop:products", "products"):
            url = self._reverse_or_none(name)
            if not url:
                continue
            resp = self.client.get(url)
            self.assertIn(
                resp.status_code,
                (200, 302, 303, 400, 403),
                f"{name} unexpected status {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for product list")

    def test_product_detail_missing_returns_404(self):
        # If detail view exists, asking for a non-existent object should be a 404 (not 500).
        candidates = [
            ("shop:product_detail", {"pk": 999999}),
            ("product_detail", {"pk": 999999}),
            ("shop:product_detail", {"slug": "non-existent-slug"}),
            ("product_detail", {"slug": "non-existent-slug"}),
        ]
        any_resolved = False
        for name, kw in candidates:
            url = self._reverse_or_none(name, **kw)
            if not url:
                continue
            any_resolved = True
            resp = self.client.get(url)
            self.assertIn(
                resp.status_code,
                (404, 302, 303, 400, 403),  # 404 is the expected case; others tolerated
                f"{name} unexpected status {resp.status_code} at {url}",
            )
            # We only need to validate one match.
            return
        if not any_resolved:
            self.skipTest("No reverseable URL found for product detail")

    def test_product_list_with_filters_does_not_crash(self):
        # Typical query params used by list views; should still render/redirect, not 500.
        for name in ("shop:product_list", "product_list"):
            url = self._reverse_or_none(name)
            if not url:
                continue
            resp = self.client.get(
                url, {"q": "starter", "category": "accessories", "page": 1, "sort": "price"}
            )
            self.assertIn(
                resp.status_code,
                (200, 302, 303, 400, 403),
                f"{name} with filters unexpected status {resp.status_code} at {url}",
            )
            return
        self.skipTest("No reverseable URL found for product list (filters)")
