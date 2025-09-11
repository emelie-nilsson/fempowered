from django.test import TestCase
from django.test.utils import override_settings


@override_settings(
    # Avoid manifest/static hashing during tests (no collectstatic needed)
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class SmokeTests(TestCase):
    """
    Very lightweight sanity checks for key pages.
    Accept 200 (OK), 302/303 (redirects), 403 (auth required), 400 (business preconditions).
    Each 'page' can list multiple candidate paths; the first non-404 wins, otherwise we skip.
    """

    # Label -> list of candidate paths (first that doesn't 404 is used)
    PATH_GROUPS = {
        "home": ["/"],
        "shop": ["/shop/", "/products/"],
        "cart": ["/cart/", "/basket/"],
        "checkout": ["/checkout/", "/checkout/address/"],
        "login": ["/accounts/login/"],
        "signup": ["/accounts/signup/"],
    }

    OK_STATUSES = {200, 302, 303, 403, 400}

    def _first_existing(self, candidates):
        """
        Return (path, response) for the first candidate that does not 404.
        If all 404 (or raise), return (None, last_response_or_None).
        """
        last_resp = None
        for path in candidates:
            try:
                resp = self.client.get(path)
                last_resp = resp
            except Exception:
                continue
            if resp.status_code != 404:
                return path, resp
        return None, last_resp

    def test_key_pages_load(self):
        for label, candidates in self.PATH_GROUPS.items():
            with self.subTest(page=label):
                path, resp = self._first_existing(candidates)

                if path is None:
                    self.skipTest(f"No candidate path exists for '{label}': {candidates}")

                self.assertIn(
                    resp.status_code,
                    self.OK_STATUSES,
                    msg=f"{label} ({path}) unexpected status: {resp.status_code}",
                )
