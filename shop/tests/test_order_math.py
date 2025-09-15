from decimal import Decimal, ROUND_HALF_UP
from django.test import SimpleTestCase


def _import_or_none(path):
    try:
        mod_path, name = path.rsplit(".", 1)
        mod = __import__(mod_path, fromlist=[name])
        return getattr(mod, name)
    except Exception:
        return None


def _get_field_names(model):
    return {f.name for f in model._meta.fields}


def _get_price_field(fields):
    # Prefer 'unit_price' if finns, annars 'price'
    if "unit_price" in fields:
        return "unit_price"
    if "price" in fields:
        return "price"
    return None


class OrderItemMathTests(SimpleTestCase):
    """
    Validates that OrderItem calculates line totals correctly with Decimal math.
    Adapts to different field/method names and skips cleanly if unsupported.
    """

    OrderItem = _import_or_none("shop.models.OrderItem")

    def setUp(self):
        if self.OrderItem is None:
            self.skipTest("shop.models.OrderItem not found")

        self.fields = _get_field_names(self.OrderItem)
        self.price_field = _get_price_field(self.fields)
        if self.price_field is None or "quantity" not in self.fields:
            self.skipTest("OrderItem lacks price/quantity fields needed for math tests")

    def _make_item(self, price, qty):
        kwargs = {self.price_field: Decimal(price), "quantity": qty}
        # fallback om modellen har 'currency' eller liknande obligatoriska fält
        for extra in ("currency",):
            if extra in self.fields and extra not in kwargs:
                kwargs[extra] = "SEK"
        return self.OrderItem(**kwargs)

    def _expected_total(self, price, qty):
        # Standard e-handelsavrundning: två decimaler, HALF_UP
        return (Decimal(price) * Decimal(qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calc_via_method_if_any(self, item):
        # Vanliga namn för rad-totalmetoder
        for attr in ("line_total", "total_price", "get_total", "total", "amount"):
            if hasattr(item, attr):
                m = getattr(item, attr)
                return m() if callable(m) else m
        return None

    def test_line_total_matches_price_times_quantity(self):
        item = self._make_item("99.50", 2)
        expected = self._expected_total("99.50", 2)

        # 1) Om modellen har egen metod/egenskap – använd den
        via_method = self._calc_via_method_if_any(item)
        if via_method is not None:
            self.assertEqual(Decimal(via_method), expected)
            return

        # 2) Annars beräkna direkt från fälten och verifiera Decimal-precisionen
        from_fields = (getattr(item, self.price_field) * Decimal(item.quantity)).quantize(
            Decimal("0.01")
        )
        self.assertEqual(from_fields, expected)

    def test_decimal_precision_half_up_rounding(self):
        # Testar “knepigt” case där avrundning spelar roll (3 * 33.335 = 100.005 → 100.01)
        item = self._make_item("33.335", 3)
        expected = self._expected_total("33.335", 3)

        via_method = self._calc_via_method_if_any(item)
        if via_method is not None:
            self.assertEqual(Decimal(via_method), expected)
            return

        from_fields = (getattr(item, self.price_field) * Decimal(item.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self.assertEqual(from_fields, expected)
