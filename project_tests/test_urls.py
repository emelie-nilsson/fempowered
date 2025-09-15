from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from django.test.utils import override_settings


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class UrlResolutionTests(TestCase):
    """
    Verifies that key URL names can be reversed and respond with an acceptable status.
    Skips gracefully if a URL name does not exist in the project.
    """

    # Default acceptable statuses for non-detail pages
    OK_STATUSES_DEFAULT = {200, 302, 303, 403, 400}

    # Per-target overrides (e.g., detail views can legitimately be 404 if object is missing)
    OK_STATUSES_PER_LABEL = {
        "product_detail": {200, 302, 303, 403, 400, 404},
    }

    TARGETS = {
        "home": [
            ("home", [None]),
        ],
        "shop_list": [
            ("shop:product_list", [None]),
            ("product_list", [None]),
        ],
        "product_detail": [
            ("shop:product_detail", [{"pk": 1}, {"slug": "example"}, {"pk": 1, "slug": "example"}]),
            ("product_detail", [{"pk": 1}, {"slug": "example"}, {"pk": 1, "slug": "example"}]),
        ],
        "cart": [
            ("cart:view", [None]),
            ("cart_detail", [None]),
            ("cart", [None]),
        ],
        "checkout": [
            ("checkout:start", [None]),
            ("checkout:address", [None]),
            ("checkout_address", [None]),
        ],
        "auth_login": [
            ("account_login", [None]),  # django-allauth
            ("login", [None]),  # contrib.auth
        ],
        "auth_signup": [
            ("account_signup", [None]),  # django-allauth
            ("signup", [None]),
        ],
    }

    def _ok_statuses_for(self, label):
        return self.OK_STATUSES_PER_LABEL.get(label, self.OK_STATUSES_DEFAULT)

    def _reverse_first(self, name, kwargs_candidates):
        last_exc = None
        for kw in kwargs_candidates or [None]:
            try:
                if kw:
                    return reverse(name, kwargs=kw)
                return reverse(name)
            except NoReverseMatch as e:
                last_exc = e
                continue
        raise last_exc or NoReverseMatch(name)

    def test_url_names_resolve_and_respond(self):
        for label, attempts in self.TARGETS.items():
            with self.subTest(target=label):
                resolved = False
                last_error = None
                for name, kwargs_list in attempts:
                    try:
                        path = self._reverse_first(name, kwargs_list)
                        resolved = True
                        resp = self.client.get(path)
                        self.assertIn(
                            resp.status_code,
                            self._ok_statuses_for(label),
                            msg=f"{label} via '{name}' unexpected status: {resp.status_code} at {path}",
                        )
                        break  # success for this label
                    except NoReverseMatch as e:
                        last_error = e
                        continue
                if not resolved:
                    self.skipTest(
                        f"No matching URL name found for '{label}'. Last error: {last_error}"
                    )
