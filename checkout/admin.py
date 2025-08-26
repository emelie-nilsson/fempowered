from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("lineitem_total",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ("order_number", "full_name", "date", "order_total", "delivery_cost", "grand_total")
    search_fields = ("order_number", "full_name", "email", "stripe_pid")
    readonly_fields = ("order_number", "order_total", "delivery_cost", "grand_total", "date")
