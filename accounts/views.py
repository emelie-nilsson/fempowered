from django.contrib.auth.decorators import login_required
from django.shortcuts import render
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
def addresses(request):
    return render(request, "accounts/addresses.html")
