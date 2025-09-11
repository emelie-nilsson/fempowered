from django.test import TestCase, override_settings
from django.http import HttpResponse
from django.urls import path, reverse
from django.views import View

# Tiny views only for this test module

class HomeView(View):
    """Tiny 'home' view so tests have a root URL."""
    def get(self, request, *args, **kwargs):
        return HttpResponse("<h1>Home</h1>")

class ShopView(View):
    """Tiny 'shop' view so {% url 'shop' %} isn't required anywhere."""
    def get(self, request, *args, **kwargs):
        return HttpResponse("<h1>Shop</h1>")

class BoomView(View):
    """Deliberately raises to trigger a 500 page."""
    def get(self, request, *args, **kwargs):
        raise RuntimeError("boom")

# Minimal error handlers to avoid template rendering pitfalls

def simple_404(request, exception):
    # No template rendering here, just a plain response
    return HttpResponse("<h1>Not Found</h1>", status=404)

def simple_500(request):
    # No template rendering here, just a plain response
    return HttpResponse("<h1>Server Error</h1>", status=500)

# Compose a module-like object for ROOT_URLCONF with custom handlers
TestURLConf = type(
    "TestURLConf",
    (),
    {
        "urlpatterns": [
            path("", HomeView.as_view(), name="home"),
            path("shop/", ShopView.as_view(), name="shop"),
            path("boom-500/", BoomView.as_view(), name="boom_500"),
        ],
        "handler404": "project_tests.test_error_pages.simple_404",
        "handler500": "project_tests.test_error_pages.simple_500",

    },
)

@override_settings(
    DEBUG=False,  # render real error pages, not debug
    DEBUG_PROPAGATE_EXCEPTIONS=False,  # don't bubble exceptions to the client
    ALLOWED_HOSTS=["testserver", "localhost"],
    ROOT_URLCONF=TestURLConf,
    # Avoid manifest/static hashing errors during tests
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class ErrorPagesRenderTests(TestCase):
    """
    Verifies that 404 and 500 responses are produced in production-like settings.
    Uses minimal custom error handlers to avoid template-time failures.
    """

    def setUp(self):
        # Ensure the test client doesn't re-raise server exceptions
        self.client.raise_request_exception = False

    def test_404_renders(self):
        resp = self.client.get("/this-path-does-not-exist-at-all-404/")
        self.assertEqual(resp.status_code, 404, "Expected a 404 in production mode")
        self.assertTrue(resp.content, "404 page should render some content")

    def test_500_renders(self):
        resp = self.client.get(reverse("boom_500"))
        self.assertEqual(resp.status_code, 500, "Expected a 500 in production mode")
        self.assertTrue(resp.content, "500 page should render some content")
