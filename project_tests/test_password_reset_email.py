from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch
from django.core import mail
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class PasswordResetEmailTests(TestCase):
    OK = (200, 302, 303, 400, 403)

    def _reverse_or_path(self, names, fallbacks):
        for n in names:
            try:
                return reverse(n), f"reverse:{n}"
            except NoReverseMatch:
                pass
        return (fallbacks[0], f"path:{fallbacks[0]}") if fallbacks else (None, None)

    def test_password_reset_sends_email(self):
        # Arrange: create a user to reset
        User.objects.create_user(email="anna@example.com", username="anna", password="secret123")

        url, label = self._reverse_or_path(
            names=("account_reset_password", "password_reset"),
            fallbacks=["/accounts/password/reset/"],
        )
        if not url:
            self.skipTest("No password reset URL found")
            return

        # Act
        resp = self.client.post(url, {"email": "anna@example.com"}, follow=True)

        # Assert
        self.assertIn(
            resp.status_code, self.OK, f"{label} POST unexpected {resp.status_code} at {url}"
        )
        self.assertGreaterEqual(len(mail.outbox), 1, "Expected at least one email to be sent")
        self.assertIn("anna@example.com", mail.outbox[0].to, "Email should be sent to the user")
