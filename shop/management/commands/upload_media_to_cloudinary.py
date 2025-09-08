import os
from pathlib import Path
from typing import Optional

from django.core.files import File
from django.core.management.base import BaseCommand
from django.conf import settings

from shop.models import Product  # justera om din modell ligger på annan plats


def find_source_file(rel_name: str) -> Optional[Path]:
    """
    Försök hitta källfilen för ett ImageField baserat på dess relativa namn i DB,
    t.ex. 'catalog/foo.webp' eller 'details/bar.webp'.

    Ordning:
    1) MEDIA_ROOT/rel_name
    2) BASE_DIR/static/img/rel_name
    3) BASE_DIR/static/  (rekursivt sök på basnamnet)
    """
    rel_name = rel_name.lstrip("/\\")
    base_media = Path(settings.MEDIA_ROOT)

    # 1) media/<rel_name>
    cand = base_media / rel_name
    if cand.exists():
        return cand

    base_dir = Path(settings.BASE_DIR)

    # 2) static/img/<rel_name> (vanlig plats i ditt projekt)
    cand = base_dir / "static" / "img" / rel_name
    if cand.exists():
        return cand

    # 3) rekursivt: hitta basnamn var som helst under static/
    basename = os.path.basename(rel_name)
    static_root = base_dir / "static"
    if static_root.exists():
        matches = list(static_root.rglob(basename))
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Om flera träffar, välj den som innehåller 'catalog'/'details' om möjligt
            preferred = [p for p in matches if any(seg in {"catalog", "details"} for seg in p.parts)]
            if len(preferred) == 1:
                return preferred[0]
            # annars ta första som sista utväg
            return matches[0]

    return None


class Command(BaseCommand):
    help = (
        "Re-save Product image fields to upload them to the active DEFAULT storage (Cloudinary).\n"
        "Letar filer i MEDIA_ROOT, därefter static/img/<relativ path>, och till sist rekursivt i static/."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
        parser.add_argument("--limit", type=int, default=None, help="Limit number of products processed")

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
                rel_name = p.image_catalog.name  # behåll mapp/namn (t.ex. 'catalog/foo.webp')
                src = find_source_file(rel_name)
                total_fields += 1
                if src and src.exists():
                    if not opts["dry_run"]:
                        with open(src, "rb") as f:
                            # Viktigt: använd originalets RELATIVA namn så Cloudinary får mappstrukturen
                            p.image_catalog.save(rel_name, File(f), save=False)
                        changed = True
                    uploaded += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Missing source for image_catalog: {rel_name}"))
                    missing += 1

            # === image_details ===
            if getattr(p, "image_details", None) and p.image_details.name:
                rel_name = p.image_details.name  # behåll t.ex. 'details/bar.webp'
                src = find_source_file(rel_name)
                total_fields += 1
                if src and src.exists():
                    if not opts["dry_run"]:
                        with open(src, "rb") as f:
                            p.image_details.save(rel_name, File(f), save=False)
                        changed = True
                    uploaded += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Missing source for image_details: {rel_name}"))
                    missing += 1

            if changed and not opts["dry_run"]:
                p.save()

            total_products += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processed products: {total_products}, image fields seen: {total_fields}, "
            f"uploaded: {uploaded}, missing: {missing}"
        ))
        self.stdout.write(self.style.SUCCESS("Done."))
