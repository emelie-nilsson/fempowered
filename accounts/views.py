from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")

@login_required
def orders(request):
    return render(request, "accounts/orders.html", {"orders": []})

@login_required
def addresses(request):
    return render(request, "accounts/addresses.html")
