from __future__ import annotations
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.filter
def safe_media_url(p: str) -> str:
    if not p:
        return ""
    s = str(p).strip()
    if s[:4].lower() == "http":
        return s
    if s.startswith("/media/"):
        return s
    if s.startswith("media/"):
        return (
            settings.MEDIA_URL if settings.MEDIA_URL.endswith("/") else settings.MEDIA_URL + "/"
        ) + s[len("media/") :]
    if s.startswith("/static/"):
        return s
    if s.startswith("static/"):
        return static(s[len("static/") :])
    base = settings.MEDIA_URL if settings.MEDIA_URL.endswith("/") else settings.MEDIA_URL + "/"
    return base + s
