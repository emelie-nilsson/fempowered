from django.db.models import Q
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden  
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, DeleteView, ListView

from django.conf import settings

from .models import Product, Review, Favorite
from .forms import ReviewForm
from .cart import Cart


# --- Helper: has the user purchased the product? ---

def has_purchased_product(user, product):  
    return product.user_has_purchased(user)


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
    Product details + reviews (one review per user).
    Shows review form only for logged-in verified buyers who haven't reviewed yet.
    """
    product = get_object_or_404(Product, pk=pk)

    user_review = None
    has_reviewed = False
    can_review = False
    form = None

    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        has_reviewed = user_review is not None
        can_review = product.user_has_purchased(request.user) and not has_reviewed
        if can_review:
            form = ReviewForm()

    # --- Reviews list + verified-buyer badge calc ---
    reviews_qs = product.reviews.select_related("user").all()  
    reviews = list(reviews_qs)  

    # Build sets of paid buyers (user_ids and emails) for this product
    try:
        from checkout.models import OrderItem, OrderStatus
        paid_status = getattr(OrderStatus, "PAID", "paid")
    except Exception:
        from checkout.models import OrderItem
        paid_status = "paid"

    rows = OrderItem.objects.filter(
        product=product,
        order__status=paid_status,
    ).values_list("order__user_id", "order__email")

    paid_user_ids = {uid for uid, email in rows if uid}
    paid_emails   = {email for uid, email in rows if email}

    # Attach r.is_verified for the template
    for r in reviews:
        user_email = getattr(r.user, "email", None)
        r.is_verified = (r.user_id in paid_user_ids) or (user_email in paid_emails)

    return render(request, "shop/product_detail.html", {
        "product": product,
        "reviews": reviews,          # pass the list with is_verified set
        "user_review": user_review,
        "form": form,
        "can_review": can_review,
        "has_reviewed": has_reviewed,
    })



# Reviews (CRUD)

class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    login_url = reverse_lazy("account_login")  

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])

        # block duplicates
        if Review.objects.filter(product=self.product, user=request.user).exists():
            messages.info(request, "You have already reviewed this product.")
            return redirect("product_detail", pk=self.product.pk)

        # verified buyer neccessary
        if not self.product.user_has_purchased(request.user):  
            messages.error(request, "Only verified buyers can write a review.")  
            return redirect("product_detail", pk=self.product.pk)                

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # serverside-skydd (extra)
        if not self.product.user_has_purchased(self.request.user):  
            return HttpResponseForbidden("Only verified buyers can review this product.")  

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
    Context for template:
      - cart_items: list of {product, size, quantity, unit_price, line_total}
      - cart_total: sum
    """
    cart = Cart(request)
    cart_items = []
    for key, item in cart: 
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
    Update row qty. qty <= 0 means remove.
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
    Remove a row (product + optional size).
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
