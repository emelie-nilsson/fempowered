import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from shop.models import Product
from .models import Order, OrderItem

stripe.api_key = settings.STRIPE_SECRET_KEY


# Cart helpers (robust snapshot)

def _get_product_from_item(item_id, item_data):
    """
    Return a Product even if the cart has odd keys.
    Try in this order:
      1) item_id as int
      2) item_data['product_id'] / item_data['id']
      3) item_data['product']['id']
    """
    # 1) Direct from item_id
    try:
        pk = int(item_id)
        p = Product.objects.filter(pk=pk).first()
        if p:
            return p
    except (TypeError, ValueError):
        pass

    # 2) From dict fields
    if isinstance(item_data, dict):
        candidates = []
        for k in ("product_id", "id"):
            if k in item_data:
                candidates.append(item_data.get(k))
        if "product" in item_data and isinstance(item_data["product"], dict):
            candidates.append(item_data["product"].get("id") or item_data["product"].get("pk"))

        for val in candidates:
            try:
                pk = int(val)
                p = Product.objects.filter(pk=pk).first()
                if p:
                    return p
            except (TypeError, ValueError):
                continue

    return None


def _extract_quantity(item_data):
    """Extract quantity from multiple cart shapes."""
    if isinstance(item_data, int):
        return max(int(item_data), 0)

    if isinstance(item_data, dict):
        # {"quantity": 2} or {"qty": 2}
        for k in ("quantity", "qty"):
            if k in item_data:
                try:
                    return max(int(item_data[k]), 0)
                except (TypeError, ValueError):
                    return 0

        # {"items_by_size": {"M": 1, "L": 2}}
        sizes = item_data.get("items_by_size") or {}
        if isinstance(sizes, dict):
            q = 0
            for v in sizes.values():
                try:
                    q += max(int(v), 0)
                except (TypeError, ValueError):
                    pass
            return q

    return 0


def _normalized_cart_snapshot(request):
    """
    Build a normalized copy of the cart WITHOUT touching session.
    Returns: {"<product_id>": quantity}
    """
    raw = request.session.get("cart") or request.session.get("bag") or {}
    normalized = {}

    iterable = enumerate(raw) if isinstance(raw, list) else raw.items()
    for item_id, item_data in iterable:
        product = _get_product_from_item(item_id, item_data)
        if not product:
            continue
        qty = _extract_quantity(item_data)
        if qty <= 0:
            continue
        key = str(product.pk)
        normalized[key] = normalized.get(key, 0) + qty

    return normalized



# Stripe: PaymentIntent

@require_POST
def create_payment_intent(request):
    """
    Create a PaymentIntent for the current (normalized) cart.
    Returns JSON with client_secret or a 4xx JSON error.
    """
    try:
        normalized = _normalized_cart_snapshot(request)
        # Compute total from normalized snapshot
        total = Decimal("0.00")
        for item_id, qty in normalized.items():
            p = Product.objects.filter(pk=int(item_id)).first()
            if not p:
                continue
            try:
                q = max(int(qty), 0)
            except (TypeError, ValueError):
                q = 0
            total += (p.price or Decimal("0.00")) * q
    except Exception as e:
        return JsonResponse(
            {"error": f"Cart error: {e}", "debug_cart": request.session.get("cart")},
            status=400,
        )

    # Convert to minor units
    try:
        amount = int(total * 100)
    except Exception as e:
        return JsonResponse({"error": f"Amount error: {e}"}, status=400)

    if amount <= 0:
        return JsonResponse(
            {
                "error": "Your cart is empty or total is zero.",
                "debug_cart": request.session.get("cart"),
                "debug_total": str(total),
                "debug_amount": amount,
            },
            status=400,
        )

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=settings.STRIPE_CURRENCY.lower(),  # e.g. "eur"
            automatic_payment_methods={"enabled": True},
            metadata={
                "cart": json.dumps(request.session.get("cart") or {}),
                "user": request.user.id if request.user.is_authenticated else "anon",
            },
        )
        return JsonResponse({"client_secret": intent.client_secret})
    except stripe.error.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        return JsonResponse({"error": msg}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)



# Checkout pages

def checkout(request):
    """
    GET: Render checkout page (Stripe Elements).
    POST: Create Order + OrderItems after successful payment on frontend.
    """
    if request.method == "POST":
        normalized = _normalized_cart_snapshot(request)
        if not normalized:
            return redirect("checkout")

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        client_secret = request.POST.get("client_secret", "")

        # Extract PaymentIntent ID ("pi_...") from the client_secret
        stripe_pid = client_secret.split("_secret")[0] if "_secret" in client_secret else ""

        # Create the Order (pending)
        order = Order.objects.create(
            full_name=full_name or "Customer",
            email=email or "",
            phone_number=phone or "",
            stripe_pid=stripe_pid,
            # store the ORIGINAL session cart for traceability
            original_cart=json.dumps(request.session.get("cart") or request.session.get("bag") or {}),
        )

        # Create OrderItems from normalized snapshot: {"product_id": qty}
        for item_id, qty in normalized.items():
            try:
                pk = int(item_id)
            except (TypeError, ValueError):
                continue
            product = Product.objects.filter(pk=pk).first()
            if not product:
                continue
            try:
                q = max(int(qty), 0)
            except (TypeError, ValueError):
                q = 0
            if q <= 0:
                continue

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=q,
                unit_price=product.price,
            )

        # Clear the cart in session (keep format expectations in shop/cart.py)
        if "cart" in request.session:
            request.session["cart"] = {}
        if "bag" in request.session:
            request.session["bag"] = {}
        request.session.modified = True

        return redirect("checkout_success", order_number=order.order_number)

    # GET
    context = {
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "checkout/checkout.html", context)


def checkout_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "checkout/checkout_success.html", {"order": order})



# Stripe webhook

@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhooks we care about:
      - payment_intent.succeeded
      - payment_intent.payment_failed
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)  # Invalid payload
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)  # Invalid signature

    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        pid = pi.get("id")
        try:
            order = Order.objects.get(stripe_pid=pid)
            # If you add status fields later:
            # order.payment_status = "paid"
            # order.paid_at = timezone.now()
            order.save(update_fields=[])  # no-op unless you add fields above
        except Order.DoesNotExist:
            pass

    elif event["type"] == "payment_intent.payment_failed":
        pi = event["data"]["object"]
        pid = pi.get("id")
        try:
            order = Order.objects.get(stripe_pid=pid)
            # order.payment_status = "failed"
            order.save(update_fields=[])
        except Order.DoesNotExist:
            pass

    return HttpResponse(status=200)
