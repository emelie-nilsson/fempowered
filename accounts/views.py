from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from checkout.models import Order


@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")


@login_required
def orders(request):
    
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
    Visa en specifik order, t.ex. FP-000123.
    Tillåt endast om ordern ägs av användaren ELLER e-post matchar (gästköp).
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
    
    return render(request, "accounts/addresses.html")
