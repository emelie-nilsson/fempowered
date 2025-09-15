from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    # avoid hashed static-problem in render
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class CsrfPresenceSmokeTests(TestCase):
    """
    Verify CSRF-token in GET-rendern.
    Adapt to different URLs.
    """

    def _reverse_first(self, candidates):
        for name in candidates:
            try:
                return reverse(name), name
            except NoReverseMatch:
                continue
        return None, None

    def _assert_has_csrf(self, resp, label):
        self.assertEqual(resp.status_code, 200, f"{label} should render 200 before checking csrf")
        content = resp.content.decode("utf-8", errors="ignore")
        self.assertIn("csrfmiddlewaretoken", content.lower(), f"{label} should include CSRF token")

    def test_checkout_address_has_csrf(self):
        url, name = self._reverse_first(
            ("checkout:address", "checkout_address", "checkout:start", "checkout_start")
        )
        if not url:
            self.skipTest("No checkout address URL found")
            return
        resp = self.client.get(url)
        self._assert_has_csrf(resp, name)

    def test_login_has_csrf(self):
        url, name = self._reverse_first(("account_login", "login"))
        if not url:
            # fallback-paths
            for p in ("/accounts/login/", "/login/"):
                resp = self.client.get(p)
                if resp.status_code in (200,):
                    self._assert_has_csrf(resp, f"path:{p}")
                    return
            self.skipTest("No login URL found")
            return
        resp = self.client.get(url)
        self._assert_has_csrf(resp, name)

    def test_signup_has_csrf(self):
        url, name = self._reverse_first(("account_signup", "signup"))
        if not url:
            for p in ("/accounts/signup/", "/signup/"):
                resp = self.client.get(p)
                if resp.status_code in (200,):
                    self._assert_has_csrf(resp, f"path:{p}")
                    return
            self.skipTest("No signup URL found")
            return
        resp = self.client.get(url)
        self._assert_has_csrf(resp, name)
