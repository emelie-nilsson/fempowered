# checkout/views.py
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


def _calculate_cart_total(request):
    """Sum the cart robustly; supports multiple cart shapes."""
    cart = request.session.get("cart")
    if cart is None:
        cart = request.session.get("bag")  # some projects use 'bag'
    cart = cart or {}

    total = Decimal("0.00")

    for item_id, item_data in cart.items():
        # Keys i sessionen är ofta strängar
        try:
            pk = int(item_id)
        except (TypeError, ValueError):
            # Om du använder andra id-typer, hämta utan cast:
            product = Product.objects.filter(pk=item_id).first()
            if not product:
                continue
        else:
            product = Product.objects.filter(pk=pk).first()
            if not product:
                continue

        price = product.price or Decimal("0.00")

        # 1) Enkel form: {"12": 2}
        if isinstance(item_data, int):
            qty = max(int(item_data), 0)
            total += price * qty
            continue

        # 2) Dict-former
        data = item_data or {}

        # 2a) {"12": {"quantity": 2}} eller {"12": {"qty": 2}}
        if "quantity" in data or "qty" in data:
            try:
                qty = max(int(data.get("quantity", data.get("qty", 0))), 0)
            except (TypeError, ValueError):
                qty = 0
            total += price * qty
            continue

        # 2b) {"12": {"items_by_size": {"M": 1, "L": 2}}}
        sizes = data.get("items_by_size") or {}
        if isinstance(sizes, dict):
            for _size, s_qty in sizes.items():
                try:
                    q = max(int(s_qty), 0)
                except (TypeError, ValueError):
                    q = 0
                total += price * q
            continue

        # 2c) fallback: ignorera okända former
        # (vill du, kan du logga här)
        continue

    return total




@require_POST
def create_payment_intent(request):
    try:
        total = _calculate_cart_total(request)
    except Exception as e:
        return JsonResponse({"error": f"Cart error: {e}"}, status=400)

    try:
        amount = int(total * 100)
    except Exception as e:
        return JsonResponse({"error": f"Amount error: {e}"}, status=400)

    if amount <= 0:
        # Skicka tillbaka ett litet snapshot som hjälp
        return JsonResponse({
            "error": "Your cart is empty or total is zero.",
            "debug_cart": request.session.get("cart") or request.session.get("bag"),
            "debug_total": str(total),
            "debug_amount": amount,
        }, status=400)

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=settings.STRIPE_CURRENCY.lower(),
            automatic_payment_methods={"enabled": True},
            metadata={
                "cart": json.dumps(request.session.get("cart") or request.session.get("bag") or {}),
                "user": request.user.id if request.user.is_authenticated else "anon",
            },
        )
        return JsonResponse({"client_secret": intent.client_secret})
    except stripe.error.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        return JsonResponse({"error": msg}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def checkout(request):
    """
    GET: Render checkout page (Stripe Elements).
    POST: Create Order + OrderItems (after payment succeeded on frontend).
    """
    if request.method == "POST":
        cart = request.session.get("cart", {})
        if not cart:
            return redirect("checkout")

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        client_secret = request.POST.get("client_secret", "")

        # Extract PaymentIntent ID ("pi_...") from the client_secret
        stripe_pid = client_secret.split("_secret")[0] if "_secret" in client_secret else ""

        # Create the Order (pending); items below
        order = Order.objects.create(
            full_name=full_name or "Customer",
            email=email or "",
            phone_number=phone or "",
            stripe_pid=stripe_pid,
            original_cart=json.dumps(cart),
        )

        # Create OrderItems from cart
        for item_id, item_data in cart.items():
            product = get_object_or_404(Product, pk=item_id)
            if isinstance(item_data, int):
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data,
                    unit_price=product.price,
                )
            else:
                for size, qty in item_data.get("items_by_size", {}).items():
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        size=size,
                        quantity=qty,
                        unit_price=product.price,
                    )

        # Clear the cart and go to success page
        request.session["cart"] = {}
        return redirect("checkout_success", order_number=order.order_number)

    # GET
    context = {
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "checkout/checkout.html", context)


def checkout_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    return render(request, "checkout/checkout_success.html", {"order": order})


#  Webhook 

@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhooks. We care about:
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

    # Process events
    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]  # contains id, amount, etc.
        pid = pi.get("id")
        # Mark order as paid if it exists
        try:
            order = Order.objects.get(stripe_pid=pid)
           
            # order.payment_status = "paid"
            # order.paid_at = timezone.now()
            order.save(update_fields=[])  
        except Order.DoesNotExist:
            # Order is created in POST /checkout.
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
