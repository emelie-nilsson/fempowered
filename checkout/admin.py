from django.contrib import admin
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "email", "status", "total_eur", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email", "full_name", "id")

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
        ("Order", {
            "fields": ("id", "status", "created_at")
        }),
        ("Kund", {
            "fields": ("full_name", "email", "phone")
        }),
        ("Leveransadress", {
            "fields": ("address1", "address2", "postal_code", "city", "country")
        }),
        ("Fakturaadress", {
            "fields": (
                "billing_same_as_shipping",
                "billing_address1", "billing_address2",
                "billing_postal_code", "billing_city", "billing_country",
            )
        }),
        ("Frakt & totals", {
            "fields": ("shipping_method", "shipping_cost", "subtotal", "total")
        }),
        ("Stripe", {
            "fields": ("payment_intent_id", "stripe_receipt_url")
        }),
    )

    # Total in euro 
    def _format_eur(self, cents: int) -> str:
        if cents is None:
            return "€0.00"
        return f"€{cents/100:.2f}"

    def total_eur(self, obj):
        return self._format_eur(obj.total)
    total_eur.short_description = "Total (€)"
