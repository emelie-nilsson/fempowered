# shop/management/commands/upload_media_to_cloudinary.py
import os
import re
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from shop.models import Product  # justera vid behov

MEDIA_PREFIX = "media/"
# Cloudinary lägger ofta till ett slump-suffix, t.ex. _kjffvo, _a1b2c3d
CLOUDINARY_SUFFIX_RE = re.compile(r"_[a-z0-9]{4,12}$", re.IGNORECASE)


def normalize_rel_name(rel_name: str, subdir_hint: str) -> str:
    """
    Rensa upp ett rel_name från DB:
    - ta bort ledande 'media/'
    - ta bort dubbelmapp (catalog/catalog eller details/details)
    - om suffix som '_abc123' finns på slutet: ta bort det
    - säkerställ att det landar under 'catalog/<name>' eller 'details/<name>' enligt subdir_hint
    - returnera relativt namn UTAN 'media/'-prefix och UTAN filändelse
    """
    rel = rel_name.strip().lstrip("/\\")
    # ta bort ledande "media/"
    if rel.startswith(MEDIA_PREFIX):
        rel = rel[len(MEDIA_PREFIX):]

    # split till parts och ta bort ev. dubblerad första mapp
    parts = [p for p in rel.split("/") if p]
    if len(parts) >= 2 and parts[0] == parts[1]:
        parts = [parts[0]] + parts[2:]

    # om första delen inte är 'catalog' eller 'details', försök baserat på hint
    if not parts or parts[0] not in {"catalog", "details"}:
        parts = [subdir_hint] + parts

    # basename utan extension
    basename = os.path.basename(parts[-1])
    stem, ext = os.path.splitext(basename)
    # ta bort cloudinary-suffix i slutet av namnet (om det inte finns extension)
    stem = CLOUDINARY_SUFFIX_RE.sub("", stem)

    # sätt tillbaka
    parts[-1] = stem  # utan extension
    return "/".join(parts)  # t.ex. "catalog/backpack_catalog"


def find_source_file(clean_rel_noext: str) -> Optional[Path]:
    """
    Leta efter källfilen i följande ordning:
    1) static/img/<clean_rel_noext>.(webp|png|jpg|jpeg)
    2) media/<clean_rel_noext>.(webp|png|jpg|jpeg)
    3) rekursivt i static/: fil vars namn börjar med basename (utan ext)
    """
    base_dir = Path(settings.BASE_DIR)
    static_img = base_dir / "static" / "img"
    media_root = Path(settings.MEDIA_ROOT)

    exts = (".webp", ".png", ".jpg", ".jpeg")

    # 1) static/img/...
    for ext in exts:
        cand = static_img / f"{clean_rel_noext}{ext}"
        if cand.exists():
            return cand

    # 2) media/...
    for ext in exts:
        cand = media_root / f"{clean_rel_noext}{ext}"
        if cand.exists():
            return cand

    # 3) rekursiv sökning i static/
    basename_noext = os.path.basename(clean_rel_noext)
    static_root = base_dir / "static"
    if static_root.exists():
        # matcha filer där filnamns-stem börjar med basename_noext
        for p in static_root.rglob("*"):
            if p.is_file():
                stem = p.stem
                if stem == basename_noext or stem.startswith(basename_noext + "_"):
                    if p.suffix.lower() in exts:
                        return p

    return None


def ensure_media_prefixed_target(clean_rel_noext: str) -> str:
    """Bygg mål-namn på formen 'media/<clean_rel_noext>.webp'."""
    return f"{MEDIA_PREFIX}{clean_rel_noext}.webp"


class Command(BaseCommand):
    help = (
        "Re-save Product.image_catalog / image_details to upload to default storage (Cloudinary).\n"
        "Rensar Cloudinary-suffix, fixar dubbla mappar, hittar filer i static/img/ eller media/, "
        "och sparar om dem under 'media/catalog|details/<name>.webp'."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Lista utan att ladda upp")
        parser.add_argument("--limit", type=int, default=None, help="Begränsa antal produkter")

    def handle(self, *args, **opts):
        qs = Product.objects.all().order_by("id")
        if opts["limit"]:
            qs = qs[: opts["limit"]]

        total_products = 0
        total_fields = 0
        uploaded = 0
        missing = 0

        for p in qs:
            changed = False

            # === image_catalog ===
            if getattr(p, "image_catalog", None) and p.image_catalog.name:
                total_fields += 1
                clean_rel = normalize_rel_name(p.image_catalog.name, subdir_hint="catalog")
                src = find_source_file(clean_rel)
                if src:
                    target_name = ensure_media_prefixed_target(clean_rel)
                    if not opts["dry_run"]:
                        with open(src, "rb") as f:
                            p.image_catalog.save(target_name, File(f), save=False)
                        changed = True
                    uploaded += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Missing source for image_catalog: {p.image_catalog.name} -> {clean_rel}"))
                    missing += 1

            # === image_details ===
            if getattr(p, "image_details", None) and p.image_details.name:
                total_fields += 1
                clean_rel = normalize_rel_name(p.image_details.name, subdir_hint="details")
                src = find_source_file(clean_rel)
                if src:
                    target_name = ensure_media_prefixed_target(clean_rel)
                    if not opts["dry_run"]:
                        with open(src, "rb") as f:
                            p.image_details.save(target_name, File(f), save=False)
                        changed = True
                    uploaded += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Missing source for image_details: {p.image_details.name} -> {clean_rel}"))
                    missing += 1

            if changed and not opts["dry_run"]:
                p.save(update_fields=["image_catalog", "image_details"])

            total_products += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processed products: {total_products}, image fields seen: {total_fields}, uploaded: {uploaded}, missing: {missing}"
        ))
        self.stdout.write(self.style.SUCCESS("Done."))
