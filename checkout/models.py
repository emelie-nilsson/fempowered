from django.conf import settings
from django.db import models
from django.utils import timezone
from shop.models import Product


class ShippingMethod(models.TextChoices):
    # Storefront labels can stay Swedish; internal values are stable slugs.
    STANDARD = "standard", "Standard (2–4 days)"
    EXPRESS = "express", "Express (1–2 days)"


# Status
class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"    


class Order(models.Model):
    """
    Customer order created at step 1 (address/shipping) and paid at step 2 (Stripe).
    All monetary amounts are stored as integer euro cents.
    """
    # Optional link to the authenticated user (guest checkout allowed)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
        db_index=True,
    )

    # Contact
    full_name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField(blank=True, default="", db_index=True)
    phone = models.CharField(max_length=40, blank=True, default="")

    # Shipping address
    address1 = models.CharField(max_length=255, blank=True, default="")
    address2 = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, default="SE")  # ISO-2 country code

    # Billing address
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_address1 = models.CharField(max_length=255, blank=True, default="")
    billing_address2 = models.CharField(max_length=255, blank=True, default="")
    billing_postal_code = models.CharField(max_length=20, blank=True, default="")
    billing_city = models.CharField(max_length=80, blank=True, default="")
    billing_country = models.CharField(max_length=2, blank=True, default="")

    # Shipping & totals (EUR in cents)
    shipping_method = models.CharField(
        max_length=20, choices=ShippingMethod.choices, default=ShippingMethod.STANDARD
    )
    shipping_cost = models.IntegerField(default=0)  # euro cents
    subtotal = models.IntegerField(default=0)       # euro cents
    total = models.IntegerField(default=0)          # euro cents

    # Stripe
    payment_intent_id = models.CharField(max_length=120, blank=True, default="")
    stripe_receipt_url = models.URLField(blank=True, default="")

    # Status & timestamps
    status = models.CharField(
        max_length=20,
        default=OrderStatus.PENDING,   
        choices=OrderStatus.choices,   
        db_index=True,                 
    )
    # Use default=timezone.now (NO auto_now_add) to avoid interactive prompts on existing rows
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def order_number(self) -> str:
        return f"FP-{self.id:06d}"

    def __str__(self) -> str:
        return f"{self.order_number()} — {self.email}"
    
    
    @property
    def display_number(self) -> str:
        return self.order_number()

    
    @property
    def is_paid(self) -> bool:
        return self.status == OrderStatus.PAID

    def __str__(self) -> str:
        return f"{self.order_number()} — {self.email}"


class OrderItem(models.Model):
    """
    Single purchased line item.
    Keep an optional FK to Product for convenience, and also freeze name/price
    at purchase time for stable history. All amounts are integer euro cents.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    # Optional FK; line still exists if product is later deleted
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )

    # Frozen fields
    product_name = models.CharField(max_length=255, blank=True, default="")
    unit_price = models.IntegerField(default=0)  # euro cents
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=8, blank=True, default="")

    class Meta:
        verbose_name = "Order item"
        verbose_name_plural = "Order items"

    @property
    def line_total(self) -> int:
        return int(self.unit_price) * int(self.quantity)

    def __str__(self) -> str:
        base = f"{self.product_name} × {self.quantity}"
        return f"{base} ({self.size})" if self.size else base

    def save(self, *args, **kwargs):
        """
        If a Product FK is present but frozen fields are missing, populate them
        from Product before saving.
        """
        if self.product:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.unit_price:
                # Assuming Product.price is a Decimal in EUR (e.g., 49.99)
                price_decimal = getattr(self.product, "price", None)
                if price_decimal is not None:
                    self.unit_price = int(round(float(price_decimal) * 100))
        super().save(*args, **kwargs)
