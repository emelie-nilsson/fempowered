from django.urls import path
from . import views

urlpatterns = [
    # Step 1: address & shipping
    path("address/", views.address_view, name="checkout_address"),

    # Step 2: payment
    path("payment/", views.payment_view, name="checkout_payment"),

    # AJAX confirm after Stripe success
    path("confirm/", views.confirm_view, name="checkout_confirm"),

    # Success page
    path("success/<str:order_number>/", views.success_view, name="checkout_success"),

    # Optional webhook 
    path("webhook/", views.stripe_webhook, name="checkout_webhook"),
]
