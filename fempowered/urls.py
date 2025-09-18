from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve as static_serve
from home import views


# Route used by project_tests.test_error_pages
def _boom_500(request):
    raise RuntimeError("boom")


# Soft-disable Allauth's Email management page
def email_management_disabled(request, *args, **kwargs):
    messages.info(request, "Email management is disabled.")
    # Redirect to home 
    return redirect("/")


urlpatterns = [
    path("admin/", admin.site.urls),
    # Core pages
    path("", views.index, name="home"),
    path("about/", views.about, name="about"),
    # Apps
    path("shop/", include("shop.urls")),
    path("account/", include("accounts.urls")),
    path("checkout/", include("checkout.urls")),
    path("contact/", include("contact.urls")),

    # Override Allauth email page BEFORE including allauth.urls
    path("accounts/email/", email_management_disabled, name="account_email"),

    # Allauth
    path("accounts/", include("allauth.urls")),
    # Error test route
    path("boom-500/", _boom_500, name="boom_500"),
]

# Serve media files from MEDIA_ROOT at /media/ 
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
]

# Error handlers
handler404 = "fempowered.error_handlers.handler404"
handler500 = "fempowered.error_handlers.handler500"
