# checkout/models.py
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from shop.models import Product  # Import the Product model from the shop app


def _generate_order_number():
    """Generate a unique order number using UUID."""
    return uuid.uuid4().hex.upper()


SIZE_CHOICES = [
    ("XS", "XS"),
    ("S", "S"),
    ("M", "M"),
    ("L", "L"),
    ("XL", "XL"),
]


class Order(models.Model):
    """
    Represents a customer order.
    Stores order totals, user reference, and Stripe payment ID.
    """
    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="orders"
    )

    # Customer information
    full_name = models.CharField(max_length=80)
    email = models.EmailField()
    phone_number = models.CharField(max_length=32, blank=True)

    date = models.DateTimeField(default=timezone.now)

    # Totals
    order_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Stripe integration
    stripe_pid = models.CharField(
        max_length=255, blank=True, help_text="Stripe PaymentIntent ID"
    )
    original_cart = models.TextField(
        blank=True,
        help_text="Snapshot of the cart at the time of purchase (JSON string).",
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        """Assign an order number if not set, then save the order."""
        if not self.order_number:
            self.order_number = _generate_order_number()
        super().save(*args, **kwargs)

    def update_totals(self):
        """Recalculate totals based on order items."""
        line_total = self.items.aggregate(
            total=models.Sum("lineitem_total")
        )["total"] or Decimal("0.00")

        self.order_total = line_total

        # Example: free delivery over 1000, otherwise 59
        self.delivery_cost = Decimal("0.00") if self.order_total >= Decimal("1000") else Decimal("59.00")

        self.grand_total = self.order_total + self.delivery_cost
        self.save(update_fields=["order_total", "delivery_cost", "grand_total"])


class OrderItem(models.Model):
    """
    Represents a single item within an order.
    Stores product, quantity, size, and line total.
    """
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_items"
    )
    size = models.CharField(
        max_length=4, choices=SIZE_CHOICES, null=True, blank=True,
        help_text="Empty if product has no size."
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    lineitem_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def __str__(self):
        base = f"{self.product.name} x {self.quantity}"
        return f"{base} ({self.size})" if self.size else base

    def save(self, *args, **kwargs):
        """
        Calculate the line item total before saving.
        Update the order totals after saving.
        """
        if not self.unit_price:
            self.unit_price = self.product.price
        self.lineitem_total = (self.unit_price or Decimal("0")) * self.quantity
        super().save(*args, **kwargs)
        self.order.update_totals()
