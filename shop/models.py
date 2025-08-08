from django.db import models

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Clothes', 'Clothes'),
        ('Accessories', 'Accessories'),
        ('Equipment', 'Equipment'),
    ]

    name = models.CharField(max_length=255)
    color = models.CharField(max_length=50, blank=True, null=True)
    hex = models.CharField(max_length=7, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    image_catalog = models.ImageField(upload_to='catalog/', blank=True, null=True)
    image_details = models.ImageField(upload_to='details/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.color})" if self.color else self.name
