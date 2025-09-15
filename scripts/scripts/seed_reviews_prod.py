from django.contrib.auth import get_user_model
from shop.models import Product, Review

AUTHOR_EMAIL = "emelie.nilsson021@gmail.com"  # prod-kontot som ska stå som författare

User = get_user_model()
user, created_user = User.objects.get_or_create(
    email=AUTHOR_EMAIL, defaults={"username": AUTHOR_EMAIL.split("@")[0]}
)
if created_user:
    user.set_unusable_password()
    user.save()

data = [
    {
        "product": "Barbell with weights",
        "rating": 5,
        "title": "Great starter barbell set",
        "body": "Sturdy bar, snug plates, smooth sleeve. Excellent value for a home gym!",
    },
    {
        "product": "Cropped t-shirt",
        "rating": 5,
        "title": "Flattering crop length",
        "body": "Boxy but not bulky, perfect with high-waist bottoms!",
    },
    {
        "product": "Oversized t-shirt",
        "rating": 5,
        "title": "Clean fit, great cotton",
        "body": "Smooth fabric, holds shape after washes and has that prefect oversized fit!",
    },
    {
        "product": "Shorts with inner shorts",
        "rating": 5,
        "title": "Stay-put comfort",
        "body": "Lightweight outer, supportive liner, and no chafing, even on long sessions. Finally a pair of shorts that I actually can workout in!",
    },
    {
        "product": "Lifting belt",
        "rating": 5,
        "title": "Solid support",
        "body": "Stiff where it counts, secure buckle, noticeable core stability on heavy lifts.",
    },
    {
        "product": "Sweatpants",
        "rating": 5,
        "title": "Perfect everyday joggers",
        "body": "Thick but breathable, tapered fit, and pockets that actually hold stuff.",
    },
    {
        "product": "Hoodie with drawstring",
        "rating": 5,
        "title": "Cozy and well-made",
        "body": "Soft fleece, true-to-size, love the drawstring. It's my new go-to layer.",
    },
]


def find_product_by_name(name):
    p = Product.objects.filter(name__iexact=name).first()
    if not p:
        p = Product.objects.filter(name__icontains=name).first()
    return p


created, updated, missing = 0, 0, []
for d in data:
    p = find_product_by_name(d["product"])
    if not p:
        missing.append(d["product"])
        continue
    obj, was_created = Review.objects.update_or_create(
        user=user,
        product=p,
        defaults={"rating": d["rating"], "title": d["title"], "body": d["body"]},
    )
    created += int(was_created)
    updated += int(not was_created)

print(f"Created: {created}, Updated: {updated}, Missing products: {missing}")
