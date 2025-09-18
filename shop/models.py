from pathlib import Path
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.templatetags.static import static
from django.db.models import Avg, Q
from django.utils import timezone


class Product(models.Model):
    # Choices matching fixtures
    CATEGORY_CHOICES = [
        ("Clothing", "Clothing"),
        ("Clothes", "Clothes"),  
        ("Accessories", "Accessories"),
        ("Equipment", "Equipment"),
        ("Strength Equipment", "Strength Equipment"),
    ]

    name = models.CharField(max_length=255)
    color = models.CharField(max_length=50, blank=True, null=True)
    hex = models.CharField(max_length=7, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)

    image_catalog = models.ImageField(upload_to="catalog/", blank=True, null=True)
    image_details = models.ImageField(upload_to="details/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.color})" if self.color else self.name

    def is_favorited_by(self, user):
        return user.is_authenticated and self.favorited_by.filter(user=user).exists()

    # Helpers
    def _resolve_media_url(self, field_name: str, base_subdir: str):
        f = getattr(self, field_name, None)
        name = getattr(f, "name", "") if f else ""
        media_root = Path(settings.MEDIA_ROOT)

        if name:
            full = media_root / name
            if full.exists():
                try:
                    return f.url
                except Exception:
                    return settings.MEDIA_URL + name.replace("\\", "/")

            base = media_root / base_subdir
            if base.exists():
                matches = list(base.rglob(Path(name).name))
                if matches:
                    rel = matches[0].relative_to(media_root).as_posix()
                    return settings.MEDIA_URL + rel

        return None

    @property
    def catalog_image_url(self):
        return self._resolve_media_url("image_catalog", "catalog") or static("img/placeholder.webp")

    @property
    def detail_image_url(self):
        return self._resolve_media_url("image_details", "details") or self.catalog_image_url

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def average_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    # Reviews / Verified buyer helpers 
    def user_has_purchased(self, user) -> bool:  
        """
        Return True if the user is logged in and has at least one *paid* 
        order line for this product – either via Order.user or via the same email 
        (if the purchase was made as a guest).
        """
        if not getattr(user, "is_authenticated", False):
            return False
        try:

            from checkout.models import OrderItem, OrderStatus

            paid_status = getattr(OrderStatus, "PAID", "paid")
        except Exception:
            from checkout.models import OrderItem

            paid_status = "paid"

        return (
            OrderItem.objects.filter(
                product=self,
                order__status=paid_status,
            )
            .filter(Q(order__user=user) | Q(order__email=user.email))
            .exists()
        )

    def has_user_reviewed(self, user) -> bool:
        """ True if the user has already submitted a review for this product."""
        if not getattr(user, "is_authenticated", False):
            return False
        return self.reviews.filter(user=user).exists()

    def user_can_review(self, user) -> bool:
        """True if logged in, verified buyer, and has not yet submitted a review"""
        return self.user_has_purchased(user) and not self.has_user_reviewed(user)

    class Meta:
        # Stop duplicates
        constraints = [
            models.UniqueConstraint(
                fields=["name", "color"],
                condition=Q(color__isnull=False),
                name="uq_product_name_color_when_color_not_null",
            ),
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(color__isnull=True),
                name="uq_product_name_when_color_is_null",
            ),
        ]


class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reviews", on_delete=models.CASCADE
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "user")  # one review per user and product
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product} - {self.user} ({self.rating})"


# Favorites


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    product = models.ForeignKey(
        "shop.Product", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_user_product_favorite")
        ]

    def __str__(self):
        return f"{self.user} ❤ {self.product}"
