from django.db.models import Q
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, DeleteView

from .models import Product, Review
from .forms import ReviewForm

from django.views.decorators.http import require_POST
from .cart import Cart


def product_list(request):
    qs = Product.objects.all()

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '').strip()
    color = request.GET.get('color', '').strip()
    sort = request.GET.get('sort', 'name_asc')

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat:
        qs = qs.filter(category__iexact=cat)  
    if color:
        qs = qs.filter(color__iexact=color)

    sort_map = {
        'name_asc': 'name',
        'name_desc': '-name',
        'price_asc': 'price',
        'price_desc': '-price',
        'newest': '-id',
    }
    qs = qs.order_by(sort_map.get(sort, 'name'))

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # filters)
    categories = (Product.objects
                  .exclude(category__isnull=True).exclude(category__exact='')
                  .values_list('category', flat=True).distinct().order_by('category'))
    colors = (Product.objects
              .exclude(color__isnull=True).exclude(color__exact='')
              .values_list('color', flat=True).distinct().order_by('color'))

    ctx = {
        'page_obj': page_obj,
        'q': q, 'cat': cat, 'color': color, 'sort': sort,
        'categories': categories,
        'colors': colors,
    }
    return render(request, 'shop/product_list.html', ctx)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    user_review = None
    form = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
        if not user_review:
            form = ReviewForm()

    reviews = product.reviews.select_related("user")

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'user_review': user_review,
        'form': form,
    })


# ----- Reviews (CRUD registered users) -----

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


def cart_detail(request):
    cart = Cart(request)
    return render(request, "shop/cart_detail.html", {"cart": cart})

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    qty = int(request.POST.get("quantity", 1))
    size = request.POST.get("size") or None
    cart.add(product, quantity=qty, size=size)
    messages.success(request, "Added to cart.")
    return redirect("cart_detail")

@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    qty = int(request.POST.get("quantity", 1))
    size = request.POST.get("size") or None
    cart.add(product, quantity=qty, size=size, override=True)
    messages.info(request, "Cart updated.")
    return redirect("cart_detail")

@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    size = request.POST.get("size") or None
    cart.remove(product, size=size)
    messages.warning(request, "Removed from cart.")
    return redirect("cart_detail")
