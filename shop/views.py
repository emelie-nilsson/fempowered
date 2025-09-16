from django.db.models import Q
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView, ListView

from django.conf import settings

from .models import Product, Review, Favorite
from .forms import ReviewForm
from .cart import Cart

# Import OrderItem to verify exact variant purchases
try:
    # If you have a dedicated OrderStatus enum, you can adapt here
    from checkout.models import OrderItem
except Exception:
    OrderItem = None  # Will fail loudly if used without being present


# Purchase verification helpers
def _paid_statuses():
    """
    Returns a list of statuses considered 'paid/fulfilled'.
    Can be overridden via settings.ORDER_PAID_STATUSES.
    """
    return getattr(settings, "ORDER_PAID_STATUSES", ["paid", "fulfilled", "delivered"])


def has_purchased_exact_variant(user, product) -> bool:
    """
    Returns True if the given user has purchased THIS exact product variant.
    Uses OrderItem -> order.user and order.email as fallback.
    """
    if OrderItem is None:
        return False

    statuses = _paid_statuses()

    # Logged-in purchase check by user relation
    if user.is_authenticated:
        if OrderItem.objects.filter(
            order__user=user,
            product=product,
            order__status__in=statuses,
        ).exists():
            return True

        # Optional: fallback by email for guest checkout matched to this user's email
        if user.email:
            if OrderItem.objects.filter(
                order__email__iexact=user.email,
                product=product,
                order__status__in=statuses,
            ).exists():
                return True

    return False


# Helpers for cart session dedupe
def _norm_size(val):
    """Normalize size values so None/''/'NA' are treated as None."""
    if val is None:
        return None
    s = str(val).strip()
    return None if s == "" or s.upper() == "NA" else s


def _delete_matching_lines_in_session(session, product_id, size):
    """
    Remove ALL lines in the session cart that match the same product+size,
    regardless of how the key/structure looks ("7", "7:M", nested dict, etc.).
    Returns True if anything was removed.
    """
    removed_any = False
    pid = str(product_id)
    size = _norm_size(size)

    for container_key in ("cart", "bag"):
        data = session.get(container_key)
        if not isinstance(data, dict):
            continue

        to_delete = []
        for k, v in list(data.items()):
            ks = str(k)

            # Option 1: key-based shapes
            if ks == pid and size is None:
                to_delete.append(k)
                continue
            if size is not None and ks == f"{pid}:{size}":
                to_delete.append(k)
                continue
            # Common "no size" variants in the key
            if size is None and ks in (f"{pid}:None", f"{pid}:", f"{pid}:NA"):
                to_delete.append(k)
                continue

            # Option 2: nested dict shapes
            if isinstance(v, dict):
                v_pid = str(v.get("product_id") or v.get("id") or "").strip()
                v_size = _norm_size(v.get("size"))
                if v_pid == pid and v_size == size:
                    to_delete.append(k)
                    continue

        if to_delete:
            for k in to_delete:
                try:
                    del data[k]
                    removed_any = True
                except KeyError:
                    pass
            session[container_key] = data  # write back

    if removed_any:
        session.modified = True
    return removed_any


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

    categories = (
        Product.objects.exclude(category__isnull=True)
        .exclude(category__exact="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    colors = (
        Product.objects.exclude(color__isnull=True)
        .exclude(color__exact="")
        .values_list("color", flat=True)
        .distinct()
        .order_by("color")
    )

    favorite_ids = set()
    if request.user.is_authenticated:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user, product__in=qs).values_list(
                "product_id", flat=True
            )
        )

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "cat": cat,
        "color": color,
        "sort": sort,
        "categories": categories,
        "colors": colors,
        "favorite_ids": favorite_ids,
    }
    return render(request, "shop/product_list.html", ctx)


def product_detail(request, pk):
    """
    Product details + reviews (one review per user).
    Shows review form only for logged-in verified buyers who haven't reviewed yet.
    Verified-buyer badges are computed from OrderItem for THIS exact product.
    """
    product = get_object_or_404(Product, pk=pk)

    # Favorite state for current user (sync heart on detail page)
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()

    user_review = None
    has_reviewed = False
    can_review = False
    form = None

    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        has_reviewed = user_review is not None
        can_review = has_purchased_exact_variant(request.user, product) and not has_reviewed
        if can_review:
            form = ReviewForm()

    # Reviews list + verified-buyer badge calc
    reviews_qs = product.reviews.select_related("user").all()
    reviews = list(reviews_qs)

    statuses = _paid_statuses()
    if OrderItem is not None:
        rows = OrderItem.objects.filter(
            product=product,
            order__status__in=statuses,
        ).values_list("order__user_id", "order__email")
    else:
        rows = []

    paid_user_ids = {uid for uid, email in rows if uid}
    paid_emails = {email for uid, email in rows if email}

    # Attach r.is_verified for the template
    for r in reviews:
        user_email = getattr(r.user, "email", None)
        r.is_verified = (r.user_id in paid_user_ids) or (user_email in paid_emails)

    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
            "reviews": reviews,  # list with is_verified set
            "user_review": user_review,
            "form": form,
            "can_review": can_review,
            "has_reviewed": has_reviewed,
            "is_favorite": is_favorite,
        },
    )


# Reviews (CRUD)
class ReviewCreateView(LoginRequiredMixin, CreateView):
    """
    Creates a review. Enforces:
      - one review per user per product
      - verified buyer for THIS exact variant (via OrderItem)
    Renders a consistent form (same look as edit) via shop/review_form.html
    (even if most users submit from product_detail).
    """

    model = Review
    form_class = ReviewForm
    login_url = reverse_lazy("account_login")
    template_name = "shop/review_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, pk=kwargs["pk"])

        # Block duplicates
        if Review.objects.filter(product=self.product, user=request.user).exists():
            messages.info(request, "You have already reviewed this product.")
            return redirect("product_detail", pk=self.product.pk)

        # Verified buyer is required for THIS exact variant
        if not has_purchased_exact_variant(request.user, self.product):
            messages.error(request, "Only verified buyers can write a review.")
            return redirect("product_detail", pk=self.product.pk)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Defense-in-depth: server-side verification
        if not has_purchased_exact_variant(self.request.user, self.product):
            return HttpResponseForbidden("Only verified buyers can review this product.")

        form.instance.product = self.product
        form.instance.user = self.request.user
        messages.success(self.request, "Review created.")
        return super().form_valid(form)

    def form_invalid(self, form):
        # Show errors nicely instead of 500 page
        messages.error(self.request, "Please fix the errors below.")
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.product
        ctx["is_edit"] = False
        ctx["review"] = None
        return ctx

    def get_success_url(self):
        return reverse("product_detail", kwargs={"pk": self.product.pk})



class OwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.get_object().user == self.request.user


class ReviewUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """
    Edits an existing review using the same form & template as create.
    """

    model = Review
    form_class = ReviewForm
    template_name = "shop/review_form.html"
    login_url = reverse_lazy("account_login")

    def get_queryset(self):
        """Extra safety: only allow editing own reviews."""
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(user=self.request.user)
        return qs.none()

    def form_valid(self, form):
        messages.success(self.request, "Review updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        review = self.object
        ctx["product"] = review.product
        ctx["is_edit"] = True
        ctx["review"] = review
        return ctx

    def get_success_url(self):
        return reverse("product_detail", kwargs={"pk": self.object.product.pk})


@login_required
@require_POST
def review_delete(request, pk):
    """
    POST-only delete. Requires owner. Redirects back to the product detail.
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)
    product_id = review.product_id
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect("product_detail", pk=product_id)


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
        # Prefer explicit size from the item; if missing, derive from key
        raw_size = item.get("size")
        if not raw_size and ":" in str(key):
            raw_size = str(key).split(":", 1)[1] or None

        # Normalize "NA"/empty to None so the template won't show a bogus pill
        size = None if raw_size in (None, "", "NA") else raw_size

        cart_items.append(
            {
                "key": key,
                "product": item["product"],
                "size": size,
                "quantity": item["quantity"],
                "unit_price": item["price"],  # Decimal
                "line_total": item["total_price"],  # Decimal
            }
        )
    context = {
        "cart_items": cart_items,
        "cart_total": cart.total(),
    }
    return render(request, "shop/cart.html", context)


@require_POST
def cart_add(request, product_id):
    """
    Add to cart. Default qty=1.
    Stores the exact variant PK in the session so checkout creates
    OrderItems pointing to the exact color/variant purchased.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1
    qty = max(qty, 1)

    size = _norm_size(request.POST.get("size"))
    cart.add(product, quantity=qty, size=size)
    messages.success(request, "Added to cart.")
    return redirect("cart_detail")


@require_POST
def cart_update(request, product_id):
    """
    Update row quantity. qty <= 0 means remove.
    To avoid duplicate lines, we first delete any existing line(s)
    for the same product+size from the raw session, then add with override=True.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    size = _norm_size(request.POST.get("size"))

    # 1) Clean up duplicates in the session for the same product+size
    _delete_matching_lines_in_session(request.session, product_id, size)

    # 2) Perform update
    if qty <= 0:
        cart.remove(product, size=size)
        messages.info(request, "Item removed.")
    else:
        cart.add(product, quantity=qty, size=size, override=True)
        messages.info(request, "Cart updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request):
    """
    Remove a cart line (product + optional size) via POST.
    Works with multiple possible cart session shapes:
    - key "product_id:size" or "product_id"
    - nested dicts per key containing {'product_id': ..., 'size': ...}
    Supports both 'cart' and legacy 'bag' session keys.
    """
    product_id = request.POST.get("product_id")
    size = _norm_size(request.POST.get("size"))

    if not product_id:
        messages.error(request, "Missing product id.")
        return redirect("cart_detail")

    # 1) Try the Cart class first
    try:
        cart = Cart(request)
        before_keys = [str(k) for (k, _item) in cart]
        product = get_object_or_404(Product, pk=product_id)
        cart.remove(product, size=size)
        after_keys = [str(k) for (k, _item) in cart]
        if set(before_keys) != set(after_keys):
            messages.warning(request, "Removed from cart.")
            return redirect("cart_detail")
    except Exception:
        pass

    # 2) Fallback: mutate raw session dict(s)
    removed_any = _delete_matching_lines_in_session(request.session, product_id, size)

    if removed_any:
        messages.warning(request, "Removed from cart.")
    else:
        messages.info(request, "Item not found in cart (nothing removed).")

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


# Utilities
def cart_reset(request):
    """One-time: clear any broken cart shapes in session."""
    request.session["cart"] = {}
    if "bag" in request.session:
        request.session["bag"] = {}
    request.session.modified = True
    return redirect("cart_detail")
