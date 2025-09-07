from django.test import SimpleTestCase
from django.contrib.auth import get_user_model


def _import_or_none(path):
    try:
        mod_path, name = path.rsplit(".", 1)
        mod = __import__(mod_path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None


class ShopModelStrTests(SimpleTestCase):
    Category = _import_or_none("shop.models.Category")
    Product = _import_or_none("shop.models.Product")
    Review = _import_or_none("shop.models.Review")
    Order = _import_or_none("shop.models.Order")
    OrderItem = _import_or_none("shop.models.OrderItem")

    def test_category_str(self):
        if self.Category is None:
            self.skipTest("shop.models.Category not found")
        fields = {f.name for f in self.Category._meta.fields}
        kwargs = {}
        if "name" in fields:
            kwargs["name"] = "Accessories"
        elif "title" in fields:
            kwargs["title"] = "Accessories"
        if "slug" in fields:
            kwargs.setdefault("slug", "accessories")
        obj = self.Category(**kwargs)
        s = str(obj)
        self.assertTrue(s.strip(), "__str__ should not be empty")
        if "name" in kwargs:
            self.assertEqual(s, kwargs["name"])
        elif "title" in kwargs:
            self.assertEqual(s, kwargs["title"])

    def test_product_str(self):
        if self.Product is None:
            self.skipTest("shop.models.Product not found")
        fields = {f.name for f in self.Product._meta.fields}
        kwargs = {}
        if "name" in fields:
            kwargs["name"] = "Starter Kit"
        elif "title" in fields:
            kwargs["title"] = "Starter Kit"
        if "slug" in fields:
            kwargs.setdefault("slug", "starter-kit")
        if "sku" in fields:
            kwargs.setdefault("sku", "SKU-TEST-001")
        if "price" in fields:
            kwargs["price"] = "199.00"
        obj = self.Product(**kwargs)
        s = str(obj)
        self.assertTrue(s.strip(), "__str__ should not be empty")
        if "name" in kwargs:
            self.assertEqual(s, kwargs["name"])
        elif "title" in kwargs:
            self.assertEqual(s, kwargs["title"])

    def test_review_str(self):
        if self.Review is None:
            self.skipTest("shop.models.Review not found")
        if self.Product is None:
            self.skipTest("shop.models.Product not found (needed for Review FK)")

        # Create unsaved instances to satisfy __str__ dependencies
        product_fields = {f.name for f in self.Product._meta.fields}
        product_kwargs = {}
        if "name" in product_fields:
            product_kwargs["name"] = "Starter Kit"
        elif "title" in product_fields:
            product_kwargs["title"] = "Starter Kit"
        if "slug" in product_fields:
            product_kwargs.setdefault("slug", "starter-kit")
        if "sku" in product_fields:
            product_kwargs.setdefault("sku", "SKU-REV-001")
        if "price" in product_fields:
            product_kwargs.setdefault("price", "199.00")
        product = self.Product(**product_kwargs)

        User = get_user_model()
        # Minimal unsaved user; __str__ usually uses username/email
        user = User(username="anna")  # no save()

        # Build Review with required FKs so __str__ can access them
        review_fields = {f.name for f in self.Review._meta.fields}
        review_kwargs = {"product": product, "user": user}
        if "rating" in review_fields:
            review_kwargs["rating"] = 5
        if "title" in review_fields:
            review_kwargs["title"] = "Great product"

        obj = self.Review(**review_kwargs)
        s = str(obj)
        self.assertTrue(s.strip(), "__str__ should not be empty")

    def test_order_str(self):
        if self.Order is None:
            self.skipTest("shop.models.Order not found")
        fields = {f.name for f in self.Order._meta.fields}
        kwargs = {}
        if "order_number" in fields:
            kwargs["order_number"] = "ORD-1001"
        if "email" in fields:
            kwargs["email"] = "anna@example.com"
        obj = self.Order(**kwargs)
        s = str(obj)
        self.assertTrue(s.strip(), "__str__ should not be empty")

    def test_order_item_str(self):
        if self.OrderItem is None:
            self.skipTest("shop.models.OrderItem not found")
        fields = {f.name for f in self.OrderItem._meta.fields}
        kwargs = {}
        if "quantity" in fields:
            kwargs["quantity"] = 2
        if "unit_price" in fields:
            kwargs["unit_price"] = "99.50"
        if "price" in fields and "unit_price" not in fields:
            kwargs["price"] = "99.50"
        obj = self.OrderItem(**kwargs)
        s = str(obj)
        self.assertTrue(s.strip(), "__str__ should not be empty")
