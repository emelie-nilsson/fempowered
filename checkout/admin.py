from django.contrib import admin
from .models import Order, OrderItem


# Helper functions
def format_eur(cents: int) -> str:
    """Convert an integer amount in cents to a formatted Euro string."""
    if cents is None:
        return "€0.00"
    try:
        return f"€{cents/100:.2f}"
    except Exception:
        return "€0.00"


# Inline for order items
class OrderItemInline(admin.TabularInline):
    """
    Displays order items directly on the Order page in the admin.
    Assumptions about OrderItem fields:
      - product: FK to Product (specific variant/color)
      - quantity: integer amount
      - unit_price: price in cents (field name may vary)
      - line_total: total for the line (field name may vary)
    If your field names differ, adjust the methods below accordingly.
    """

    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "quantity", "unit_price_eur", "line_total_eur")
    fields = ("product", "quantity", "unit_price_eur", "line_total_eur")

    def _unit_price_cents(self, obj) -> int | None:
        """Try to detect the correct field for unit price in cents."""
        for name in ("unit_price", "price", "unit_price_cents", "price_cents"):
            if hasattr(obj, name):
                return getattr(obj, name)
        return None

    def _line_total_cents(self, obj) -> int | None:
        """
        Try to detect the correct field for line total in cents.
        If not present, calculate as quantity * unit_price.
        """
        for name in ("line_total", "total", "line_total_cents", "total_cents"):
            if hasattr(obj, name):
                return getattr(obj, name)
        unit = self._unit_price_cents(obj)
        if unit is not None and getattr(obj, "quantity", None):
            try:
                return int(unit) * int(obj.quantity)
            except Exception:
                return None
        return None

    def unit_price_eur(self, obj):
        """Formatted unit price in Euro."""
        return format_eur(self._unit_price_cents(obj))

    unit_price_eur.short_description = "Unit price (€)"

    def line_total_eur(self, obj):
        """Formatted line total in Euro."""
        return format_eur(self._line_total_cents(obj))

    line_total_eur.short_description = "Line total (€)"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for the Order model."""

    list_display = ("order_number", "email", "status", "total_eur", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "email", "full_name", "id")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    inlines = [OrderItemInline]

    readonly_fields = (
        "id",
        "created_at",
        "payment_intent_id",
        "stripe_receipt_url",
        "subtotal",
        "shipping_cost",
        "total",
    )

    fieldsets = (
        ("Order", {"fields": ("id", "order_number", "status", "created_at")}),
        ("Customer", {"fields": ("full_name", "email", "phone")}),
        (
            "Shipping address",
            {"fields": ("address1", "address2", "postal_code", "city", "country")},
        ),
        (
            "Billing address",
            {
                "fields": (
                    "billing_same_as_shipping",
                    "billing_address1",
                    "billing_address2",
                    "billing_postal_code",
                    "billing_city",
                    "billing_country",
                )
            },
        ),
        (
            "Shipping & totals",
            {"fields": ("shipping_method", "shipping_cost", "subtotal", "total")},
        ),
        ("Stripe", {"fields": ("payment_intent_id", "stripe_receipt_url")}),
    )

    def total_eur(self, obj):
        """Formatted order total in Euro."""
        return format_eur(obj.total)

    total_eur.short_description = "Total (€)"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin configuration for the OrderItem model (optional, for overview)."""

    list_display = ("order", "product", "quantity")
    search_fields = ("order__order_number", "product__name")
    list_select_related = ("order", "product")
