from decimal import Decimal
from django.test import TestCase
from django.test.utils import override_settings
from importlib import import_module


def _import_or_none(path):
    try:
        module_path, name = path.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, name)
    except Exception:
        return None


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class OrderTotalSmokeTests(TestCase):
    """
    Smoke-level tests for order totals:
    - If an Order model exists and exposes a total-like method, calling it should not crash.
    - If we can also find an OrderItem model with price & quantity-like fields and an obvious relation,
      we add a line and expect total > 0.
    Tests skip gracefully if the project doesn't match these assumptions.
    """

    Order = _import_or_none("shop.models.Order")
    OrderItem = _import_or_none("shop.models.OrderItem")

    TOTAL_METHOD_CANDIDATES = ("total", "get_total", "grand_total", "total_amount")
    RELATION_CANDIDATES = ("items", "lines", "orderitem_set", "order_items", "line_items")

    PRICE_FIELD_CANDIDATES = ("unit_price", "price")
    QTY_FIELD_CANDIDATES = ("quantity", "qty", "amount")

    def setUp(self):
        if self.Order is None:
            self.skipTest("shop.models.Order not found")
        # Find a total-like method on Order
        self.total_attr = None
        for name in self.TOTAL_METHOD_CANDIDATES:
            if hasattr(self.Order, name):
                self.total_attr = name
                break
        if not self.total_attr:
            self.skipTest("No total-like method found on Order")

    def _call_total(self, order):
        attr = getattr(order, self.total_attr)
        return attr() if callable(attr) else attr

    def _find_rel_manager(self, order):
        """Return (manager, rel_name) for items if any, else (None, None)."""
        for rel in self.RELATION_CANDIDATES:
            if hasattr(order, rel):
                mgr = getattr(order, rel)
                # Support reverse manager (has .create/.add) or list-like
                if hasattr(mgr, "create") or hasattr(mgr, "add") or hasattr(mgr, "all"):
                    return mgr, rel
        return None, None

    def _choose_field(self, model, candidates):
        names = {f.name for f in model._meta.fields}
        for c in candidates:
            if c in names:
                return c
        return None

    def _minimal_order_kwargs(self):
        """Attempt to satisfy obvious required fields if present (very conservative)."""
        names = {f.name for f in self.Order._meta.fields}
        kw = {}
        # Common “status” defaults
        for f in ("status", "state"):
            if f in names:
                # choose a harmless string if CharField; skip DB constraints
                kw[f] = "draft"
        # Currency defaults
        for f in ("currency",):
            if f in names:
                kw[f] = "SEK"
        return kw

    def _minimal_item_kwargs(self, price_field, qty_field):
        """Build kwargs for OrderItem without saving."""
        names = {f.name for f in self.OrderItem._meta.fields}
        kw = {price_field: Decimal("25.00"), qty_field: 2}
        if "currency" in names:
            kw["currency"] = "SEK"
        return kw

    def test_order_total_callable_does_not_crash(self):
        # Unsaved Order instance with minimal kwargs; calling total should not raise.
        order = self.Order(**self._minimal_order_kwargs())
        try:
            _ = self._call_total(order)
        except Exception as e:
            self.fail(f"Calling Order.{self.total_attr}() raised: {e!r}")

    def test_order_total_with_single_item_if_possible(self):
        if self.OrderItem is None:
            self.skipTest("OrderItem model not found")

        # Determine price & quantity fields
        price_field = self._choose_field(self.OrderItem, self.PRICE_FIELD_CANDIDATES)
        qty_field = self._choose_field(self.OrderItem, self.QTY_FIELD_CANDIDATES)
        if not price_field or not qty_field:
            self.skipTest("OrderItem lacks recognizable price/quantity fields")

        # Create & save order to get a PK if relation requires it
        order = self.Order.objects.create(**self._minimal_order_kwargs())

        # Find relation manager from order to items
        mgr, rel_name = self._find_rel_manager(order)
        if mgr is None:
            self.skipTest("Could not locate an Order -> OrderItem relation")

        # Try adding an item via manager if possible; otherwise fallback to direct create with FK
        try:
            item_kwargs = self._minimal_item_kwargs(price_field, qty_field)
            # Use manager.create if available (reverse relation)
            if hasattr(mgr, "create"):
                mgr.create(**item_kwargs)
            else:
                # Fall back: create item with order FK if name looks like 'order' or similar
                names = {f.name for f in self.OrderItem._meta.fields}
                fk_name = "order" if "order" in names else None
                if not fk_name:
                    self.skipTest("No manager.create and no obvious FK to attach OrderItem")
                item_kwargs[fk_name] = order
                self.OrderItem.objects.create(**item_kwargs)
        except Exception as e:
            self.skipTest(f"Unable to attach an OrderItem to Order ({e!r})")

        # Now total should be > 0
        try:
            total = self._call_total(order)
        except Exception as e:
            self.fail(f"Order total raised after adding item: {e!r}")

        # Accept Decimal or numeric
        if isinstance(total, (int, float)):
            self.assertGreater(total, 0, "Order total should be > 0 after adding an item")
        else:
            self.assertIsInstance(total, Decimal, "Order total should be a Decimal or numeric")
            self.assertGreater(total, Decimal("0"), "Order total should be > 0 after adding an item")
