import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.urls import reverse

from .forms import CheckoutAddressForm
from .models import Order, OrderItem, ShippingMethod
from shop.models import Product
from accounts.models import UserAddress   


try:  
    from .models import OrderStatus  
except Exception:  
    class OrderStatus:             
        PENDING = "pending"
        PAID = "paid"
        FAILED = "failed"
        CANCELLED = "cancelled"

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------- Cart helpers (normalize multiple formats to one shape) ----------

def normalize_cart_items(request):
    """
    Normalize various session cart formats into a list of dicts:
        [{'pid': 123, 'name': 'Name', 'qty': 2, 'price_cent': 5499, 'size': 'M'}, ...]

    Supports:
      A) {"123": {"name":..., "qty": 2, "price_cent": 5499, "size": "M"}}
      B) {"123": {"name":..., "qty": 2, "price": "54.99"}}  # euros -> cents
      C) Boutique Ado "bag":
         - {"123": 2}
         - {"123": {"items_by_size": {"S":1,"M":2}}}

    Falls back to DB (shop.Product) for name/price when missing.
    """
    raw = request.session.get("cart") or request.session.get("bag") or {}
    items = []

    for pid, val in raw.items():
        try:
            pid_int = int(pid)
        except Exception:
            pid_int = None

        def db_info():
            name, cents = f"Product {pid}", 0
            if pid_int:
                try:
                    p = Product.objects.get(pk=pid_int)
                    name = p.name
                    # p.price expected to be Decimal euros
                    cents = int(round(float(p.price) * 100))
                except Exception:
                    pass
            return name, cents

        # Case: dict with flat qty/price fields (non BA)
        if isinstance(val, dict) and "items_by_size" not in val:
            qty = int(val.get("qty") or val.get("quantity") or 0)
            size = (val.get("size") or "")[:8]
            # price in cents or euros
            if "price_cent" in val:
                price_cents = int(val["price_cent"])
            elif "price" in val or "price_eur" in val:
                eur = float(val.get("price") or val.get("price_eur") or 0)
                price_cents = int(round(eur * 100))
            else:
                _, price_cents = db_info()
            name = val.get("name") or db_info()[0]
            if qty > 0:
                items.append({
                    "pid": pid_int, "name": name, "qty": qty,
                    "price_cent": price_cents, "size": size
                })
            continue

        # Case: Boutique Ado style (no sizes)
        if isinstance(val, int):
            qty = int(val)
            name, price_cents = db_info()
            if qty > 0:
                items.append({
                    "pid": pid_int, "name": name, "qty": qty,
                    "price_cent": price_cents, "size": ""
                })
            continue

        # Case: Boutique Ado style with items_by_size
        if isinstance(val, dict) and "items_by_size" in val:
            name, price_cents = db_info()
            for size, qty in (val.get("items_by_size") or {}).items():
                qty = int(qty)
                if qty > 0:
                    items.append({
                        "pid": pid_int, "name": name, "qty": qty,
                        "price_cent": price_cents, "size": (size or "")[:8]
                    })
            continue

    return items


def get_cart_subtotal_cents(request) -> int:
    return sum(i["price_cent"] * i["qty"] for i in normalize_cart_items(request))


def describe_cart_for_metadata(request) -> str:
    items = normalize_cart_items(request)
    return ", ".join(f"{i['name']}x{i['qty']}" for i in items)[:200]


def calc_shipping_cost_cents(method: str, subtotal: int) -> int:
    """
    Simple example:
      - Standard: free over €80, else €5.90
      - Express: €9.90
    """
    if method == ShippingMethod.EXPRESS:
        return 990   # €9.90
    return 0 if subtotal >= 8000 else 590  # €5.90 or free over €80


# ---------- STEP 1: Address & shipping ----------

@require_http_methods(["GET", "POST"])
def address_view(request):
    # Prefill from saved address for logged-in users
    initial = {}
    if request.user.is_authenticated:
        initial["email"] = request.user.email
        try:
            ua = request.user.address  
        except (AttributeError, UserAddress.DoesNotExist):
            ua = None
        if ua:
            initial.update({
                "full_name": ua.full_name or (request.user.get_full_name() or ""),
                "phone": ua.phone or "",
                "address1": ua.address1 or "",
                "address2": ua.address2 or "",
                "postal_code": ua.postal_code or "",
                "city": ua.city or "",
                "country": ua.country or "SE",
                "billing_same_as_shipping": ua.billing_same_as_shipping,
                "billing_address1": ua.billing_address1 or "",
                "billing_address2": ua.billing_address2 or "",
                "billing_postal_code": ua.billing_postal_code or "",
                "billing_city": ua.billing_city or "",
                "billing_country": ua.billing_country or "",
            })

    if request.method == "POST":
        form = CheckoutAddressForm(request.POST)
        if form.is_valid():
            items = normalize_cart_items(request)
            subtotal = sum(i["price_cent"] * i["qty"] for i in items)
            if subtotal <= 0 or not items:
                return render(request, "checkout/empty_cart.html", status=400)

            data = form.cleaned_data
            shipping_cost = calc_shipping_cost_cents(data["shipping_method"], subtotal)
            total = subtotal + shipping_cost

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=data["full_name"],
                email=data["email"],
                phone=data.get("phone") or "",
                address1=data["address1"],
                address2=data.get("address2") or "",
                postal_code=data["postal_code"],
                city=data["city"],
                country=data["country"],
                billing_same_as_shipping=data["billing_same_as_shipping"],
                billing_address1=data.get("billing_address1") or "",
                billing_address2=data.get("billing_address2") or "",
                billing_postal_code=data.get("billing_postal_code") or "",
                billing_city=data.get("billing_city") or "",
                billing_country=data.get("billing_country") or "",
                shipping_method=data["shipping_method"],
                shipping_cost=shipping_cost,
                subtotal=subtotal,
                total=total,
                status=OrderStatus.PENDING, 
            )

            # Snapshot cart into OrderItems
            for it in items:
                product_fk = None
                pid_val = it.get("pid")
                if pid_val:
                    product_fk = Product.objects.filter(pk=pid_val).first()
                if not product_fk:
                    product_fk = (
                        Product.objects.filter(name__iexact=it["name"]).first()
                        or Product.objects.filter(name__icontains=it["name"]).first()
                    )
                OrderItem.objects.create(
                    order=order,
                    product=product_fk,
                    product_name=it["name"],
                    unit_price=it["price_cent"],
                    quantity=it["qty"],
                    size=it["size"],
                )

            # --- Auto-save address back to profile (logged-in users) ---
            if request.user.is_authenticated:
                ua, _ = UserAddress.objects.get_or_create(user=request.user)
                # shipping
                ua.full_name = data["full_name"]
                ua.email = data["email"]
                ua.phone = data.get("phone") or ""
                ua.address1 = data["address1"]
                ua.address2 = data.get("address2") or ""
                ua.postal_code = data["postal_code"]
                ua.city = data["city"]
                ua.country = data["country"]
                # billing
                ua.billing_same_as_shipping = data["billing_same_as_shipping"]
                if ua.billing_same_as_shipping:
                    ua.billing_address1 = ua.address1
                    ua.billing_address2 = ua.address2
                    ua.billing_postal_code = ua.postal_code
                    ua.billing_city = ua.city
                    ua.billing_country = ua.country
                else:
                    ua.billing_address1 = data.get("billing_address1") or ""
                    ua.billing_address2 = data.get("billing_address2") or ""
                    ua.billing_postal_code = data.get("billing_postal_code") or ""
                    ua.billing_city = data.get("billing_city") or ""
                    ua.billing_country = data.get("billing_country") or ""
                ua.save()
            

            # Link order in session and continue to payment
            request.session["checkout_order_id"] = order.id
            request.session.modified = True
            return redirect("checkout_payment")
    else:
        form = CheckoutAddressForm(initial=initial)

    return render(request, "checkout/checkout_address.html", {"form": form})


# ---------- STEP 2: Payment (Stripe) ----------

@ensure_csrf_cookie  # ensure CSRF cookie is set for subsequent POST to /confirm/
@require_http_methods(["GET"])
def payment_view(request):
    order_id = request.session.get("checkout_order_id")
    if not order_id:
        return redirect("checkout_address")

    order = get_object_or_404(Order, id=order_id, status="pending")

    # Create or retrieve PaymentIntent
    if not order.payment_intent_id:
        intent = stripe.PaymentIntent.create(
            amount=order.total,             # euro cents
            currency="eur",
            receipt_email=order.email,
            metadata={
                "order_id": str(order.id),
                "email": order.email,
                "cart": describe_cart_for_metadata(request),
            },
            automatic_payment_methods={"enabled": True},
        )
        order.payment_intent_id = intent.id
        order.save(update_fields=["payment_intent_id"])
        client_secret = intent.client_secret
    else:
        intent = stripe.PaymentIntent.retrieve(order.payment_intent_id)
        client_secret = intent.client_secret

    context = {
        "order": order,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        "client_secret": client_secret,
    }
    return render(request, "checkout/checkout_payment.html", context)


# ---------- Confirm (AJAX from payment page AFTER Stripe success) ----------

@require_http_methods(["POST"])
def confirm_view(request):
    # 1) Parse JSON from fetch
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    # 2) Get order from session
    order_id = request.session.get("checkout_order_id")
    if not order_id:
        return JsonResponse({"ok": False, "error": "Missing order_id"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    # 3) Ensure correct PaymentIntent is being confirmed
    pi_id = payload.get("payment_intent_id")
    if not pi_id or pi_id != order.payment_intent_id:
        return JsonResponse({"ok": False, "error": "PaymentIntent mismatch"}, status=400)

    # 4) Retrieve PaymentIntent from Stripe
    try:
        pi = stripe.PaymentIntent.retrieve(pi_id)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"Stripe retrieve failed: {e}"}, status=400)

    if pi.status != "succeeded":
        return JsonResponse({"ok": False, "error": "Payment not succeeded"}, status=400)

    # 5) Get receipt URL via latest_charge (PaymentIntent doesn't include charges by default)
    receipt_url = ""
    try:
        latest_charge_id = getattr(pi, "latest_charge", None)
        if latest_charge_id:
            ch = stripe.Charge.retrieve(latest_charge_id)
            receipt_url = getattr(ch, "receipt_url", "") or (ch.get("receipt_url") if hasattr(ch, "get") else "")
    except Exception:
        # Not critical; lack of receipt link shouldn't block order completion
        pass

    ## 6) Mark order as paid + store receipt + (NEW) attach user if logged in
    order.status = OrderStatus.PAID                      
    order.stripe_receipt_url = receipt_url
    if request.user.is_authenticated and order.user is None:  
        order.user = request.user                               
        order.save(update_fields=["status", "stripe_receipt_url", "user"])  
    else:
        order.save(update_fields=["status", "stripe_receipt_url"])

    # 7) Clear cart and unlink the order from the session
    request.session["cart"] = {}
    request.session.pop("checkout_order_id", None)
    request.session.modified = True

    # 8) Return redirect URL to success page
    redirect_url = reverse("checkout_success", args=[order.order_number()])
    return JsonResponse({"ok": True, "redirect_url": redirect_url})


# ---------- Success page ----------

def success_view(request, order_number: str):
    # order_number like "FP-000123" -> extract numeric id
    try:
        order_id = int(order_number.split("-")[-1])
    except Exception:
        return HttpResponseBadRequest("Invalid order number")
    order = get_object_or_404(Order, id=order_id)

    if request.user.is_authenticated and order.user is None:
        order.user = request.user
        
        if order.status != OrderStatus.PAID:
            order.status = OrderStatus.PAID
        order.save(update_fields=["user", "status"])

    return render(request, "checkout/success.html", {"order": order})


# ---------- Stripe Webhook (server-to-server, optional in dev) ----------

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    wh_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    # Verify signature if a secret is configured
    if wh_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=wh_secret
            )
        except Exception:
            return HttpResponseBadRequest("Invalid signature")
    else:
        # Fallback (dev environments): parse without verification
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("Invalid payload")

    event_type = event["type"] if isinstance(event, dict) else event.type
    obj = event["data"]["object"] if isinstance(event, dict) else event.data.object

    # Helper to mark order paid/failed
    def _update_order_from_pi(pi, paid: bool):
        # metadata access for both dict and StripeObject
        meta = (pi.get("metadata") if isinstance(pi, dict) else getattr(pi, "metadata", None)) or {}
        order_id_val = meta.get("order_id")
        if not order_id_val:
            return
        try:
            order = Order.objects.get(id=int(order_id_val))
        except (Order.DoesNotExist, ValueError):
            return

        if paid and order.status != OrderStatus.PAID:
            receipt_url = ""
            try:
                latest_charge_id = (pi.get("latest_charge") if isinstance(pi, dict) else getattr(pi, "latest_charge", None))
                if latest_charge_id:
                    ch = stripe.Charge.retrieve(latest_charge_id)
                    receipt_url = getattr(ch, "receipt_url", "") or (ch.get("receipt_url") if hasattr(ch, "get") else "")
            except Exception:
                pass

            order.status = OrderStatus.PAID
            order.stripe_receipt_url = receipt_url
            order.save(update_fields=["status", "stripe_receipt_url"])
        elif not paid and order.status != OrderStatus.FAILED:
            order.status = OrderStatus.FAILED
            order.save(update_fields=["status"])

    # Handle events
    if event_type == "payment_intent.succeeded":
        _update_order_from_pi(obj, paid=True)
    elif event_type == "payment_intent.payment_failed":
        _update_order_from_pi(obj, paid=False)

    return HttpResponse(status=200)

