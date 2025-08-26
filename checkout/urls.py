from django.urls import path
from . import views

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("create-payment-intent/", views.create_payment_intent, name="create_payment_intent"),
    path("success/<order_number>/", views.checkout_success, name="checkout_success"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
]
