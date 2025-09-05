from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_POST

from checkout.models import Order
from .forms import UserAddressForm
from .models import UserAddress


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")


@login_required
def orders(request):
    """
    Display all orders for the logged-in user.
    Orders are matched either by user foreign key OR by email (for guest checkouts).
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
    Display a specific order, e.g. FP-000123.
    Allowed only if the order belongs to the logged-in user OR email matches (guest checkout).
    """
    try:
        order_id = int(order_number.split("-")[1])
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
    Reuse the same OneToOne instance even if soft-deleted (is_active=False),
    and re-activate on save to avoid unique constraint collisions.
    """
    try:
        ua = request.user.address  
    except UserAddress.DoesNotExist:
        ua = None  

    if request.method == "POST":
        form = UserAddressForm(request.POST, instance=ua)  
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.is_active = True  # re-activate when saved
            obj.save()
            messages.success(request, "Address saved.")
            return redirect("addresses")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        if ua:
            form = UserAddressForm(instance=ua)
        else:
            form = UserAddressForm(initial={
                "full_name": request.user.get_full_name() or "",
                "email": request.user.email,
                "country": "SE",
                "billing_same_as_shipping": True,
            })

    # No active, no delete
    return render(request, "accounts/addresses.html", {"form": form, "address": ua})


@login_required
@require_POST
def address_delete(request):
    """
    Soft-delete the saved address for the logged-in user:
    - Set is_active=False
    - Clear most fields (so it is visibly "deleted" in the UI)
    """
    addr = getattr(request.user, "address", None)

    if not addr or not addr.is_active:
        messages.info(request, "No active address to delete.")
        return redirect("addresses")

    addr.is_active = False

    # Clear fields 
    addr.full_name = ""
    addr.email = ""
    addr.phone = ""
    addr.address1 = ""
    addr.address2 = ""
    addr.postal_code = ""
    addr.city = ""
    addr.billing_same_as_shipping = True
    addr.billing_address1 = ""
    addr.billing_address2 = ""
    addr.billing_postal_code = ""
    addr.billing_city = ""
    addr.billing_country = ""

    addr.save(update_fields=[
        "is_active",
        "full_name", "email", "phone", "address1", "address2",
        "postal_code", "city",
        "billing_same_as_shipping", "billing_address1", "billing_address2",
        "billing_postal_code", "billing_city", "billing_country",
    ])

    messages.success(request, "Your address was deleted.")
    return redirect("addresses")
