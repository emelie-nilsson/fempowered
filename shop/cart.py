from decimal import Decimal, InvalidOperation
from django.conf import settings
from shop.models import Product

CART_SESSION_ID = "cart"


class Cart:
    """
    Session-backed shopping cart.

    Shape stored in session:
      {
        "<product_id>:<size-or->": {
            "product_id": <int>,
            "quantity": <int>,
            "price": "<decimal-as-string>",
            "size": <str or None>,
            "name": <str>,
        },
        ...
      }

    Notes:
    - We save price as string in session to keep it JSON-serializable.
    - Iteration returns in-memory copies with Decimal price/total, without
      mutating the session objects.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None or not isinstance(cart, dict):
            cart = {}
            self.session[CART_SESSION_ID] = cart
            self.save()
        self.cart = cart

    
    # Public API
    
    def add(self, product, quantity=1, size=None, override=False):
        """
        Add a product to the cart or update its quantity.
        Key is "<product_id>:<size-or->" so the same product with different sizes
        are tracked as separate line items.
        """
        key = f"{product.id}:{size or '-'}"

        if key not in self.cart or not isinstance(self.cart.get(key), dict):
            # Recreate a proper line item dict
            self.cart[key] = {
                "product_id": product.id,
                "quantity": 0,
                "price": str(product.price),  # store as string in session
                "size": size or None,
                "name": getattr(product, "name", str(product)),
            }

        if override:
            self.cart[key]["quantity"] = int(quantity or 0)
        else:
            self.cart[key]["quantity"] += int(quantity or 0)

        # Guard: no negatives
        if self.cart[key]["quantity"] <= 0:
            del self.cart[key]

        self.save()

    def remove(self, product, size=None):
        key = f"{product.id}:{size or '-'}"
        if key in self.cart:
            del self.cart[key]
            self.save()

    def clear(self):
        """Remove cart entirely."""
        self.session[CART_SESSION_ID] = {}
        self.cart = self.session[CART_SESSION_ID]
        self.save()

    def __len__(self):
        """
        Return total quantity of items in the cart.
        Skips malformed entries (e.g., integers).
        """
        total_qty = 0
        for item in self.cart.values():
            if isinstance(item, dict):
                try:
                    total_qty += int(item.get("quantity", 0) or 0)
                except (TypeError, ValueError):
                    continue
        return total_qty

    def total(self):
        """
        Return total price (Decimal) of current cart.
        Skips malformed entries.
        """
        total = Decimal("0.00")
        for item in self._valid_items():
            price = self._as_decimal(item.get("price", "0"))
            qty = self._as_int(item.get("quantity", 0))
            total += price * qty
        return total

    def __iter__(self):
        """
        Iterate over cart items, yielding (key, item_dict_copy) where:
          - item_dict_copy["product"] is attached
          - item_dict_copy["price"] is Decimal
          - item_dict_copy["total_price"] is Decimal(price * quantity)
        We DO NOT mutate session objects here.
        """
        valid_items = self._valid_items()
        product_ids = [itm["product_id"] for itm in valid_items]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

        for key, raw in self.cart.items():
            if not isinstance(raw, dict):
                # Skip malformed entries silently
                continue

            product = products.get(raw.get("product_id"))
            if not product:
                # Product was removed from DB; skip line
                continue

            # Work on a copy so session data stays JSON-serializable
            item = dict(raw)
            price = self._as_decimal(item.get("price", "0"))
            qty = self._as_int(item.get("quantity", 0))

            item["product"] = product
            item["price"] = price
            item["total_price"] = price * qty

            yield key, item

    def save(self):
        """Mark session as modified so it gets persisted."""
        self.session.modified = True

   
    # Internal helpers
    
    def _valid_items(self):
        """Return a list of well-formed dict items from the session cart."""
        items = []
        for item in self.cart.values():
            if not isinstance(item, dict):
                continue
            # Must have product_id and quantity
            if "product_id" not in item:
                continue
            items.append(item)
        return items

    @staticmethod
    def _as_decimal(value):
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0.00")

    @staticmethod
    def _as_int(value):
        try:
            return max(int(value or 0), 0)
        except (TypeError, ValueError):
            return 0
