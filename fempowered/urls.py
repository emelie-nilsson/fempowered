from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve as static_serve
from home import views

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

    # Allauth
    path("accounts/", include("allauth.urls")),
]

# Serve media files from MEDIA_ROOT at /media/ (works even with DEBUG=False)
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", static_serve, {"document_root": settings.MEDIA_ROOT}),
]
