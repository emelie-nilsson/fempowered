from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist

from shop.models import Product


def find_file(kind: str, filename: str) -> Optional[str]:
    """
    Recursively search MEDIA_ROOT/<kind>/** for an exact filename.
    Return media-relative POSIX path like 'catalog/clothes/foo.webp' or None.
    """
    base = Path(settings.MEDIA_ROOT) / kind
    if not base.exists():
        return None
    for p in base.rglob(filename):
        if p.is_file():
            return p.relative_to(settings.MEDIA_ROOT).as_posix()
    return None


def pick_filename(*values: Optional[str]) -> Optional[str]:
    """
    From several raw values, return the first non-empty basename.
    """
    for v in values:
        if not v:
            continue
        name = os.path.basename(str(v)).strip()
        if name:
            return name
    return None


def current_rel(val: Optional[str]) -> Optional[str]:
    """
    Convert an existing value into a media-relative path if it already points to /media/.
    e.g. '/media/catalog/x.webp' -> 'catalog/x.webp', 'media/catalog/x.webp' -> 'catalog/x.webp'
    If it already starts with 'catalog/' or 'details/', return as-is.
    Otherwise return None.
    """
    if not val:
        return None
    s = str(val).strip().replace("\\", "/")
    if s.startswith("/media/"):
        return s[len("/media/") :]
    if s.startswith("media/"):
        return s[len("media/") :]
    if s.startswith("catalog/") or s.startswith("details/"):
        return s
    return None


def has_model_field(model_cls, field_name: str) -> bool:
    """
    True only if 'field_name' is a real Django model field (not a @property).
    """
    try:
        model_cls._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False


def get_field_value(obj, name: str) -> Optional[str]:
    """
    Safely get string value from either CharField/ImageField (FieldFile) or None.
    """
    if not hasattr(obj, name):
        return None
    val = getattr(obj, name)
    if val is None:
        return None
    return str(val)


class Command(BaseCommand):
    help = (
        "Normalize Product image paths by matching files under MEDIA_ROOT/catalog/** and details/**.\n"
        "Writes media-relative paths (e.g. 'catalog/<subdir>/<file>') to REAL model fields only "
        "(e.g. image_catalog, image_detail). Use --apply to persist changes; default is dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes to the database (default is dry-run).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Only process the first N products (for testing).",
        )

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        limit = opts["limit"]

        qs = Product.objects.all().order_by("id")
        if limit:
            qs = qs[:limit]

        total = qs.count()
        changed = 0
        missing_catalog = 0
        missing_details = 0

        self.stdout.write(
            self.style.NOTICE(f"Scanning {total} products (apply={apply_changes})...")
        )

        # Determine which real fields we can write to
        # Adjust candidates if your model uses different names
        catalog_field_candidates = ["image_catalog"]
        detail_field_candidates = ["image_detail"]

        write_catalog_field = next(
            (f for f in catalog_field_candidates if has_model_field(Product, f)), None
        )
        write_detail_field = next(
            (f for f in detail_field_candidates if has_model_field(Product, f)), None
        )

        if not write_catalog_field and not write_detail_field:
            self.stderr.write(
                self.style.ERROR(
                    "No writable image fields found on Product. "
                    "Expected 'image_catalog' and/or 'image_detail'."
                )
            )
            return

        # Process
        with transaction.atomic():
            for p in qs:
                # Gather all potential raw values (stringified)
                raw_catalog_url = getattr(
                    p, "catalog_image_url", None
                )  # property (read-only), ignore on write
                raw_detail_url = getattr(
                    p, "detail_image_url", None
                )  # property (read-only), ignore on write
                raw_image_catalog = (
                    get_field_value(p, "image_catalog") if write_catalog_field else None
                )
                raw_image_detail = (
                    get_field_value(p, "image_detail") if write_detail_field else None
                )

                # Resolve existing relative paths if already correct
                rel_catalog = current_rel(
                    str(raw_catalog_url) if raw_catalog_url else None
                ) or current_rel(raw_image_catalog)
                rel_details = current_rel(
                    str(raw_detail_url) if raw_detail_url else None
                ) or current_rel(raw_image_detail)

                # If missing, try by filename search
                if not rel_catalog and write_catalog_field:
                    fname = pick_filename(
                        str(raw_catalog_url) if raw_catalog_url else None, raw_image_catalog
                    )
                    if fname:
                        found = find_file("catalog", fname)
                        if found:
                            rel_catalog = found

                if not rel_details and write_detail_field:
                    # Try detail filename first; fall back to catalog filename if needed
                    fname_d = pick_filename(
                        str(raw_detail_url) if raw_detail_url else None, raw_image_detail
                    ) or pick_filename(
                        str(raw_catalog_url) if raw_catalog_url else None, raw_image_catalog
                    )
                    if fname_d:
                        found_d = find_file("details", fname_d)
                        if found_d:
                            rel_details = found_d

                if write_catalog_field and not rel_catalog:
                    missing_catalog += 1
                if write_detail_field and not rel_details:
                    missing_details += 1

                # Prepare updates
                to_update = []

                # Only set REAL fields, never properties
                if write_catalog_field and rel_catalog:
                    # Skip if unchanged
                    if raw_image_catalog != rel_catalog:
                        setattr(p, write_catalog_field, rel_catalog)
                        to_update.append(write_catalog_field)

                if write_detail_field and rel_details:
                    if raw_image_detail != rel_details:
                        setattr(p, write_detail_field, rel_details)
                        to_update.append(write_detail_field)

                if to_update:
                    changed += 1
                    if apply_changes:
                        p.save(update_fields=list(set(to_update)))
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"#{p.pk} {p.name}: set {', '.join(sorted(set(to_update)))}"
                        )
                    )
                else:
                    self.stdout.write(f"#{p.pk} {p.name}: no changes")

            # Rollback in dry-run mode
            if not apply_changes:
                self.stdout.write(
                    self.style.WARNING("Dry-run complete (no DB changes were committed).")
                )
                transaction.set_rollback(True)

        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        self.stdout.write(f"  Products scanned : {total}")
        self.stdout.write(
            f"  Updated records  : {changed}{' (saved)' if apply_changes else ' (dry-run)'}"
        )
        if write_catalog_field:
            self.stdout.write(f"  Missing catalog  : {missing_catalog}")
        if write_detail_field:
            self.stdout.write(f"  Missing details  : {missing_details}")
