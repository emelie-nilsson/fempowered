from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model

User = get_user_model()

@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AdminSmokeTests(TestCase):
    OK = (200, 302, 303)

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.client.login(username="admin", password="adminpass")

    def test_admin_index_loads(self):
        resp = self.client.get("/admin/")
        self.assertIn(resp.status_code, self.OK, f"Admin index unexpected {resp.status_code}")

    def _try_model_changelist(self, app, model):
        try:
            url = reverse(f"admin:{app}_{model}_changelist")
        except NoReverseMatch:
            self.skipTest(f"{app}.{model} not registered in admin")
            return
        resp = self.client.get(url)
        self.assertIn(resp.status_code, self.OK, f"{app}.{model} changelist unexpected {resp.status_code} at {url}")

    def test_shop_product_in_admin(self):
        self._try_model_changelist("shop", "product")

    def test_checkout_order_in_admin(self):
        # Anpassa om din ordermodell ligger i annat app-label
        for candidate in [("checkout", "order"), ("shop", "order"), ("orders", "order")]:
            try:
                return self._try_model_changelist(*candidate)
            except AssertionError:
                raise
            except Exception:
                continue
        self.skipTest("No order model changelist found in admin")
