from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("orders/", views.orders, name="orders"),
    path("addresses/", views.addresses, name="addresses"),
]
