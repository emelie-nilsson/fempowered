from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AuthViewsSmokeTests(TestCase):
    """
    Smoke tests for auth pages (login, signup, password reset).
    Adaptive to Django auth and django-allauth; skips if route not present.
    """

    OK = (200, 302, 303, 400, 403)

    def _reverse_or_path(self, names, fallbacks=None, kwargs=None):
        for n in names:
            try:
                return reverse(n, kwargs=kwargs or None), f"reverse:{n}"
            except NoReverseMatch:
                continue
        fallbacks = fallbacks or []
        for p in fallbacks:
            return p, f"path:{p}"
        return None, None

    def _assert_ok(self, resp, label, url):
        self.assertIn(resp.status_code, self.OK, f"{label} unexpected {resp.status_code} at {url}")

    def test_login_get(self):
        url, label = self._reverse_or_path(
            names=("account_login", "login"),
            fallbacks=["/accounts/login/", "/login/"],
        )
        if not url:
            self.skipTest("No login URL found")
            return
        resp = self.client.get(url)
        self._assert_ok(resp, label, url)

    def test_login_post_invalid(self):
        url, label = self._reverse_or_path(
            names=("account_login", "login"),
            fallbacks=["/accounts/login/", "/login/"],
        )
        if not url:
            self.skipTest("No login URL found")
            return
        # Typical field names for Django or allauth:
        resp = self.client.post(url, {"login": "nope@example.com", "password": "wrong"})
        self._assert_ok(resp, f"{label} POST invalid", url)

    def test_signup_get(self):
        url, label = self._reverse_or_path(
            names=("account_signup", "signup"),
            fallbacks=["/accounts/signup/", "/signup/"],
        )
        if not url:
            self.skipTest("No signup URL found")
            return
        resp = self.client.get(url)
        self._assert_ok(resp, label, url)

    def test_password_reset_get(self):
        url, label = self._reverse_or_path(
            names=("account_reset_password", "password_reset"),
            fallbacks=["/accounts/password/reset/", "/password_reset/"],
        )
        if not url:
            self.skipTest("No password reset URL found")
            return
        resp = self.client.get(url)
        self._assert_ok(resp, label, url)
