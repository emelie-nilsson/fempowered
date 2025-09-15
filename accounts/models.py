from django.conf import settings
from django.db import models


class UserAddress(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="address",
    )

    # Shipping/contact
    full_name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    address1 = models.CharField(max_length=255, blank=True, default="")
    address2 = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, default="SE")

    # Billing
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_address1 = models.CharField(max_length=255, blank=True, default="")
    billing_address2 = models.CharField(max_length=255, blank=True, default="")
    billing_postal_code = models.CharField(max_length=20, blank=True, default="")
    billing_city = models.CharField(max_length=80, blank=True, default="")
    billing_country = models.CharField(max_length=2, blank=True, default="")

    # Management
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Address for {self.user.email}"
