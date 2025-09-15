from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_POST

from checkout.models import Order
from .forms import UserAddressForm


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")


@login_required
def orders(request):
    """
    List all orders for the logged-in user.
    Match either by FK user or by email for guest checkouts.
    """
    user = request.user
    orders_qs = (
        Order.objects
        .filter(Q(user=user) | Q(email=user.email))
        .order_by("-created_at")
        .prefetch_related("items")
    )
    return render(request, "accounts/orders.html", {"orders": orders_qs})


@login_required
def order_detail(request, order_number):
    """
    Show a specific order (e.g., FP-000123).
    Permit access if the order belongs to the user or email matches.
    """
    # Be defensive when parsing "FP-000123" -> 123
    order_id = None
    try:
        # Split by "-", take the last segment, strip leading zeros
        tail = order_number.split("-")[-1]
        order_id = int(tail.lstrip("0") or "0")
    except Exception:
        return render(request, "accounts/order_detail.html", status=404)

    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"), id=order_id
    )

    if not (order.user_id == request.user.id or order.email == request.user.email):
        return render(request, "accounts/order_detail.html", status=404)

    return render(request, "accounts/order_detail.html", {"order": order})


@login_required
def addresses(request):
    """
    Display and update the logged-in user's address.
    Reuse the same OneToOne instance (related_name='address').
    If billing_same_as_shipping is checked, mirror shipping fields to billing.
    Reactivate soft-deleted records on save.
    """
    # Get existing address instance if present (OneToOne)
    ua = getattr(request.user, "address", None)

    if request.method == "POST":
        form = UserAddressForm(request.POST, instance=ua)

        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.is_active = True  # ensure reactivation after soft delete

            # If user ticked "billing_same_as_shipping", copy shipping -> billing
            if form.cleaned_data.get("billing_same_as_shipping"):
                addr.billing_address1 = addr.address1 or ""
                addr.billing_address2 = addr.address2 or ""
                addr.billing_postal_code = addr.postal_code or ""
                addr.billing_city = addr.city or ""
                addr.billing_country = addr.country or ""

            addr.save()
            messages.success(request, "Address saved.")
            # NOTE: keep your existing URL name. If namespaced, use "accounts:addresses".
            return redirect("addresses")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        if ua:
            form = UserAddressForm(instance=ua)
        else:
            # Pre-fill sensible defaults for first-time setup
            form = UserAddressForm(initial={
                "full_name": (request.user.get_full_name() or "").strip(),
                "email": request.user.email,
                "country": "SE",  
                "billing_same_as_shipping": True,
            })

    return render(request, "accounts/addresses.html", {"form": form, "address": ua})


@login_required
@require_POST
def address_delete(request):
    """
    Soft-delete the saved address for the logged-in user:
    - Set is_active=False
    - Clear user-visible fields so the UI reflects deletion
    """
    addr = getattr(request.user, "address", None)

    if not addr or not addr.is_active:
        messages.info(request, "No active address to delete.")
        return redirect("addresses")

    addr.is_active = False

    # Clear primary (shipping) fields
    addr.full_name = ""
    addr.email = ""
    addr.phone = ""
    addr.address1 = ""
    addr.address2 = ""
    addr.postal_code = ""
    addr.city = ""
    addr.country = ""

    # Reset billing
    addr.billing_same_as_shipping = True
    addr.billing_address1 = ""
    addr.billing_address2 = ""
    addr.billing_postal_code = ""
    addr.billing_city = ""
    addr.billing_country = ""

    addr.save(update_fields=[
        "is_active",
        "full_name", "email", "phone",
        "address1", "address2", "postal_code", "city", "country",
        "billing_same_as_shipping",
        "billing_address1", "billing_address2",
        "billing_postal_code", "billing_city", "billing_country",
    ])

    messages.success(request, "Your address was deleted.")
    return redirect("addresses")
