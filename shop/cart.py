from decimal import Decimal
from django.conf import settings
from shop.models import Product

CART_SESSION_ID = "cart"

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, product, quantity=1, size=None, override=False):
        """
        Key f"{product_id}:{size or '-'}" separate sizes.
        """
        key = f"{product.id}:{size or '-'}"
        if key not in self.cart:
            self.cart[key] = {
                "product_id": product.id,
                "quantity": 0,
                "price": str(product.price),  # save as str in session
                "size": size or None,
                "name": product.name,
            }
        if override:
            self.cart[key]["quantity"] = quantity
        else:
            self.cart[key]["quantity"] += quantity
        self.save()

    def remove(self, product, size=None):
        key = f"{product.id}:{size or '-'}"
        if key in self.cart:
            del self.cart[key]
            self.save()

    def __iter__(self):
        product_ids = [item["product_id"] for item in self.cart.values()]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
        for key, item in self.cart.items():
            p = products.get(item["product_id"])
            if not p:
                continue
            # live data
            item["product"] = p
            item["price"] = Decimal(item["price"])
            item["total_price"] = item["price"] * item["quantity"]
            yield key, item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def total(self):
        from decimal import Decimal
        return sum(Decimal(i["price"]) * i["quantity"] for i in self.cart.values())

    def clear(self):
        self.session[CART_SESSION_ID] = {}
        self.save()

    def save(self):
        self.session.modified = True
