from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Optional, Iterable

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.core.exceptions import FieldDoesNotExist

from shop.models import Product  # adjust if Product is elsewhere


IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def is_model_field(model_cls, name: str) -> bool:
    try:
        model_cls._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


def stringify(val: object) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def norm_rel_path(s: str) -> str:
    """
    Normalize a candidate media-relative path string:
    - make forward slashes
    - drop leading /media/ or media/
    - collapse duplicate slashes
    - fix accidental 'catalog/media/' or 'details/media/' after the root
    - collapse duplicated roots like 'catalog/catalog/...'
    """
    s = s.replace("\\", "/").strip()

    # Strip leading /media/ or media/
    if s.startswith("/media/"):
        s = s[len("/media/") :]
    if s.startswith("media/"):
        s = s[len("media/") :]

    # Collapse duplicate slashes
    while "//" in s:
        s = s.replace("//", "/")

    # Remove accidental '/media/' after root
    for root in ("catalog", "details"):
        prefix = f"{root}/media/"
        if s.startswith(prefix):
            s = f"{root}/" + s[len(prefix) :]

    # Collapse duplicated roots (catalog/catalog/, details/details/)
    for root in ("catalog", "details"):
        dbl = f"{root}/{root}/"
        while s.startswith(dbl):
            s = f"{root}/" + s[len(dbl) :]

    return s


def rglob_images(base: Path, name_predicate) -> Optional[Path]:
    """
    Search recursively under 'base' for files for which 'name_predicate(Path)' returns True.
    Return the first match (depth-first).
    """
    if not base.exists():
        return None
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            if name_predicate(p):
                return p
    return None


def match_by_filename(base_dir: Path, stem_hint: str, subdir_hint: Optional[str]) -> Optional[Path]:
    """
    Try to find a real file for 'stem_hint' (without extension). We try, in order:
      1) exact stem match within subdir_hint if provided,
      2) exact stem match anywhere under base_dir,
      3) prefix match (file.stem startswith stem_hint) within subdir_hint,
      4) relaxed prefix (strip trailing _<random> or -<random>) anywhere.
    """
    # If we have a suggested subdir, try there first
    def in_subdir(p: Path) -> bool:
        if not subdir_hint:
            return True
        try:
            # Check if the relative path contains the hint as a directory segment
            rel = p.relative_to(base_dir).as_posix()
            return f"/{subdir_hint.strip('/')}/" in ("/" + rel + "/")
        except Exception:
            return True

    # 1) exact stem match in subdir_hint
    found = rglob_images(base_dir, lambda p: in_subdir(p) and p.stem == stem_hint)
    if found:
        return found

    # 2) exact stem match anywhere
    found = rglob_images(base_dir, lambda p: p.stem == stem_hint)
    if found:
        return found

    # 3) prefix match in subdir_hint
    found = rglob_images(base_dir, lambda p: in_subdir(p) and p.stem.startswith(stem_hint))
    if found:
        return found

    # 4) relaxed: remove trailing random token like _abc123 or -abc123 and try prefix
    relaxed = re.sub(r"([_-])[a-z0-9]{4,}$", "", stem_hint, flags=re.IGNORECASE)
    if relaxed != stem_hint:
        # exact relaxed stem in subdir
        found = rglob_images(base_dir, lambda p: in_subdir(p) and p.stem == relaxed)
        if found:
            return found
        # prefix relaxed
        found = rglob_images(base_dir, lambda p: in_subdir(p) and p.stem.startswith(relaxed))
        if found:
            return found

    return None


def ensure_ext_or_find(kind: str, rel_path: str) -> Optional[str]:
    """
    If rel_path already points to an existing image under MEDIA_ROOT, return it.
    If it has no extension or doesn't exist, try to find a matching file by stem.
    Return a corrected media-relative path or None.
    """
    media_root = Path(settings.MEDIA_ROOT)
    rel_path = norm_rel_path(rel_path)

    # Ensure it belongs to the right root (catalog or details); if neither, keep as-is for existence check
    if not (rel_path.startswith("catalog/") or rel_path.startswith("details/")):
        rel_path = f"{kind.rstrip('/')}/{rel_path.lstrip('/')}"

    abs_path = media_root / rel_path
    if abs_path.exists() and abs_path.is_file():
        return abs_path.relative_to(media_root).as_posix()

    # Extract optional subdir from the current path to prioritize
    parts = rel_path.split("/")
    subdir_hint = parts[1] if len(parts) >= 3 else None  # catalog/<subdir>/filename

    stem = Path(parts[-1]).stem  # drop any ext; may be the raw stem without extension
    base_dir = media_root / kind

    found = match_by_filename(base_dir, stem_hint=stem, subdir_hint=subdir_hint)
    if found:
        return found.relative_to(media_root).as_posix()

    return None


class Command(BaseCommand):
    help = (
        "Fix and normalize Product.image_catalog / Product.image_detail values:\n"
        "- strip stray 'media/' segments and duplicate roots\n"
        "- add real file extensions by matching actual files under media/catalog/** and media/details/**\n"
        "- write back media-relative paths like 'catalog/<subdir>/<file>.<ext>'"
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Persist changes (default: dry-run).")
        parser.add_argument("--limit", type=int, default=None, help="Only process first N products.")

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        limit = opts["limit"]

        # Ensure fields exist
        can_write_catalog = is_model_field(Product, "image_catalog")
        can_write_detail = is_model_field(Product, "image_detail")
        if not (can_write_catalog or can_write_detail):
            self.stderr.write(self.style.ERROR("No writable image fields (image_catalog/image_detail) on Product."))
            return

        qs = Product.objects.all().order_by("id")
        if limit:
            qs = qs[:limit]
        total = qs.count()

        self.stdout.write(self.style.NOTICE(f"Scanning {total} products (apply={apply_changes})..."))

        updated = 0
        missing_after = 0

        with transaction.atomic():
            for p in qs:
                before_cat = stringify(getattr(p, "image_catalog", None)) if can_write_catalog else None
                before_det = stringify(getattr(p, "image_detail", None)) if can_write_detail else None

                after_cat = None
                after_det = None

                # Catalog
                if can_write_catalog:
                    if before_cat:
                        norm = norm_rel_path(before_cat)
                        fixed = ensure_ext_or_find("catalog", norm) or norm  # keep norm even if not found (best-effort)
                        after_cat = fixed
                    else:
                        # Attempt to derive from any readable property (optional)
                        prop = stringify(getattr(p, "catalog_image_url", None))
                        if prop:
                            norm = norm_rel_path(prop)
                            fixed = ensure_ext_or_find("catalog", norm) or norm
                            after_cat = fixed

                # Details
                if can_write_detail:
                    if before_det:
                        norm = norm_rel_path(before_det)
                        fixed = ensure_ext_or_find("details", norm) or norm
                        after_det = fixed
                    else:
                        prop = stringify(getattr(p, "detail_image_url", None))
                        if prop:
                            norm = norm_rel_path(prop)
                            fixed = ensure_ext_or_find("details", norm)
                            if not fixed and can_write_catalog and (after_cat or before_cat):
                                # Fallback: use catalog stem to find a details image with same stem
                                base_for_stem = after_cat or before_cat
                                stem = Path(norm_rel_path(base_for_stem)).stem
                                fixed = match_by_filename(Path(settings.MEDIA_ROOT) / "details", stem, None)
                                fixed = fixed.relative_to(settings.MEDIA_ROOT).as_posix() if fixed else None
                            after_det = fixed or norm_rel_path(prop)

                # Decide updates
                fields_to_update = []
                if can_write_catalog and after_cat and after_cat != before_cat:
                    setattr(p, "image_catalog", after_cat)
                    fields_to_update.append("image_catalog")

                if can_write_detail and after_det and after_det != before_det:
                    setattr(p, "image_detail", after_det)
                    fields_to_update.append("image_detail")

                if fields_to_update:
                    updated += 1
                    if apply_changes:
                        p.save(update_fields=fields_to_update)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"#{p.pk} {p.name}: " +
                            ", ".join(f"{f}='{getattr(p, f)}'" for f in fields_to_update)
                        )
                    )
                else:
                    self.stdout.write(f"#{p.pk} {p.name}: no changes")

                # Track unresolved images
                final_cat = stringify(getattr(p, "image_catalog", None)) if can_write_catalog else None
                if can_write_catalog and final_cat:
                    abs_cat = (Path(settings.MEDIA_ROOT) / norm_rel_path(final_cat))
                    if not (abs_cat.exists() and abs_cat.is_file()):
                        missing_after += 1

            if not apply_changes:
                self.stdout.write(self.style.WARNING("Dry-run complete (no DB changes were committed)."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        self.stdout.write(f"  Products scanned : {total}")
        self.stdout.write(f"  Updated records  : {updated}{' (saved)' if apply_changes else ' (dry-run)'}")
        self.stdout.write(f"  Unresolved files : {missing_after}")
