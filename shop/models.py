import os
from pathlib import Path
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.templatetags.static import static
from django.db.models import Avg


class Product(models.Model):
    # Choices matching fixtures
    CATEGORY_CHOICES = [
        ('Clothing', 'Clothing'),
        ('Clothes', 'Clothes'),              # kan rensas senare
        ('Accessories', 'Accessories'),
        ('Equipment', 'Equipment'),
        ('Strength Equipment', 'Strength Equipment'),
    ]

    name = models.CharField(max_length=255)
    color = models.CharField(max_length=50, blank=True, null=True)
    hex = models.CharField(max_length=7, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)

    image_catalog = models.ImageField(upload_to='catalog/', blank=True, null=True)
    image_details = models.ImageField(upload_to='details/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.color})" if self.color else self.name

    # Helpers
    def _resolve_media_url(self, field_name: str, base_subdir: str):
        """
        1) Om fältets fil finns exakt -> returnera dess URL
        2) Annars: sök efter samma FILNAMN under media/<base_subdir>/** och returnera första träffen
        3) Om inget hittas -> None
        """
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


class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reviews", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "user")   # one review per user and product
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product} - {self.user} ({self.rating})"
