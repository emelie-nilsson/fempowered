from django.urls import path
from . import views

urlpatterns = [
    # Listing
    path("", views.product_list, name="shop"),
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),

    # Cart
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="add_to_cart"),   # alias so template's 'add_to_cart' works
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("cart/reset/", views.cart_reset, name="cart_reset"),

    # Favorites
    path("favorites/", views.FavoriteListView.as_view(), name="favorites"),
    path("favorites/toggle/<int:product_id>/", views.toggle_favorite, name="toggle_favorite"),
]
