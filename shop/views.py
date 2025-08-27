from django.db.models import Q
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from django.conf import settings

from .models import Product, Review, Favorite
from .forms import ReviewForm
from .cart import Cart


# --- Helper: have the user purchased the product? ---
# TODO: echange to actuall Order/OrderItem-modell.
def has_purchased_product(user, product):
    return False


# Products


def product_list(request):
    """
    Product list with search, filter, sort, pagination.
    """
    qs = Product.objects.all()

    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "").strip()
    color = request.GET.get("color", "").strip()
    sort = request.GET.get("sort", "name_asc")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat:
        qs = qs.filter(category__iexact=cat)
    if color:
        qs = qs.filter(color__iexact=color)

    sort_map = {
        "name_asc": "name",
        "name_desc": "-name",
        "price_asc": "price",
        "price_desc": "-price",
        "newest": "-id",
    }
    qs = qs.order_by(sort_map.get(sort, "name"))

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = (Product.objects
                  .exclude(category__isnull=True).exclude(category__exact="")
                  .values_list("category", flat=True).distinct().order_by("category"))
    colors = (Product.objects
              .exclude(color__isnull=True).exclude(color__exact="")
              .values_list("color", flat=True).distinct().order_by("color"))

    
    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user, product__in=qs)
                            .values_list("product_id", flat=True)
        )

    ctx = {
        "page_obj": page_obj,
        "q": q, "cat": cat, "color": color, "sort": sort,
        "categories": categories,
        "colors": colors,
        "favorite_ids": favorite_ids,
    }
    return render(request, "shop/product_list.html", ctx)


def product_detail(request, pk):
    """
    Product details + reviews (en recension per user).
    """
    product = get_object_or_404(Product, pk=pk)

    user_review = None
    form = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        if not user_review:
            form = ReviewForm()

  
    if hasattr(product, "reviews"):
        reviews = product.reviews.select_related("user").all()
    else:
        reviews = Review.objects.select_related("user").filter(product=product)

    return render(request, "shop/product_detail.html", {
        "product": product,
        "reviews": reviews,
        "user_review": user_review,
        "form": form,
    })



# Reviews (CRUD)

class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])
        if Review.objects.filter(product=self.product, user=request.user).exists():
            messages.info(request, "You have already reviewed this product.")
            return redirect("product_detail", pk=self.product.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.product = self.product
        form.instance.user = self.request.user
        messages.success(self.request, "Review created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("product_detail", kwargs={"pk": self.product.pk})


class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.get_object().user == self.request.user


class ReviewUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    model = Review
    form_class = ReviewForm

    def form_valid(self, form):
        messages.success(self.request, "Review updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("product_detail", kwargs={"pk": self.object.product.pk})


class ReviewDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    model = Review

    def get_success_url(self):
        messages.success(self.request, "Review deleted.")
        return reverse("product_detail", kwargs={"pk": self.object.product.pk})



# Cart

def cart_detail(request):
    """
    Context för templatet:
      - cart_items: lista med {product, size, quantity, unit_price, line_total}
      - cart_total: totalsumma
    """
    cart = Cart(request)
    cart_items = []
    for key, item in cart:  # Cart.__iter__ yieldar (key, item)
        cart_items.append({
            "key": key,
            "product": item["product"],
            "size": item.get("size"),
            "quantity": item["quantity"],
            "unit_price": item["price"],        # Decimal
            "line_total": item["total_price"],  # Decimal
        })
    context = {
        "cart_items": cart_items,
        "cart_total": cart.total(),
    }
    return render(request, "shop/cart.html", context)


@require_POST
def cart_add(request, product_id):
    """
    Add to cart. Default qty=1. 
    """
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    qty = max(qty, 1)

    size = request.POST.get("size") or None
    cart.add(product, quantity=qty, size=size)
    messages.success(request, "Added to cart.")
    return redirect("cart_detail")


@require_POST
def cart_update(request, product_id):
    """
    Uppdatera radens qty. qty <= 0 tolkar vi som remove.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    size = request.POST.get("size") or None

    if qty <= 0:
        cart.remove(product, size=size)
        messages.info(request, "Item removed.")
    else:
        cart.add(product, quantity=qty, size=size, override=True)
        messages.info(request, "Cart updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, product_id):
    """
    Ta bort en rad (produkt + ev. storlek).
    """
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    size = request.POST.get("size") or None
    cart.remove(product, size=size)
    messages.warning(request, "Removed from cart.")
    return redirect("cart_detail")



# Favorites

class FavoriteListView(LoginRequiredMixin, ListView):
    template_name = "shop/favorites.html"
    context_object_name = "favorites"
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        return Favorite.objects.select_related("product").filter(user=self.request.user)


@login_required(login_url="account_login")
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if created:
        status = "added"
    else:
        fav.delete()
        status = "removed"

    # AJAX
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": status, "product_id": product_id})

    # Non-AJAX
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("favorites")
    return HttpResponseRedirect(next_url)


# reset cart
from django.shortcuts import redirect

def cart_reset(request):
    """One-time: clear any broken cart shapes in session."""
    request.session['cart'] = {}
    if 'bag' in request.session:
        request.session['bag'] = {}
    request.session.modified = True
    return redirect('cart_detail')  
