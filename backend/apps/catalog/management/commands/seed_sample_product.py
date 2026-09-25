from decimal import Decimal

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Product, ProductImage
from apps.vendors.models import Shop

JOHN_EMAIL = "john@emall.local"
JOHN_PASSWORD = "Password123!"
SHOP_NAME = "John's Shop"
PRODUCT_NAME = "Sample USB-C Cable"
SAMPLE_IMAGE_NAMES = ["cable.png", "28_0.jpg", "28_1.jpg"]


class Command(BaseCommand):
    help = (
        "Creates (or reuses) a vendor account 'john', an approved shop, and a sample "
        "published product with images, to exercise the MinIO/S3 image storage path "
        "end-to-end. Safe to rerun."
    )

    def handle(self, *args, **options):
        john, created = User.objects.get_or_create(
            email=JOHN_EMAIL,
            defaults={
                "name": "John",
                "role": User.Role.VENDOR,
                "is_email_verified": True,
            },
        )
        john.name = "John"
        john.role = User.Role.VENDOR
        john.is_email_verified = True
        john.set_password(JOHN_PASSWORD)
        john.save()
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} vendor account: {john.email}"))

        shop, shop_created = Shop.objects.get_or_create(
            owner=john,
            name=SHOP_NAME,
            defaults={"status": Shop.Status.APPROVED, "status_changed_at": timezone.now()},
        )
        if shop.status != Shop.Status.APPROVED:
            shop.status = Shop.Status.APPROVED
            shop.status_changed_at = timezone.now()
            shop.save()
        verb = "Created" if shop_created else "Using existing"
        self.stdout.write(self.style.SUCCESS(f"{verb} shop: {shop.name} (APPROVED)"))

        try:
            category = Category.objects.get(slug="electronics")
        except Category.DoesNotExist as exc:
            raise CommandError(
                "Category 'electronics' not found — run migrations (0002_seed_categories) first."
            ) from exc

        product, product_created = Product.objects.get_or_create(
            shop=shop,
            name=PRODUCT_NAME,
            defaults={
                "category": category,
                "description": "Sample product seeded to verify MinIO image storage.",
                "price": Decimal("15000.00"),
                "stock_quantity": 25,
                "is_published": True,
            },
        )
        verb = "Created" if product_created else "Using existing"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} product: {product.name} (id={product.id})")
        )

        media_products_dir = settings.MEDIA_ROOT / "products"
        image_count = 0
        for position, filename in enumerate(SAMPLE_IMAGE_NAMES):
            source_path = media_products_dir / filename
            if not source_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"Skipping missing sample image: {source_path}")
                )
                continue
            if ProductImage.objects.filter(product=product, position=position).exists():
                image_count += 1
                continue
            with open(source_path, "rb") as fh:
                image = ProductImage(product=product, position=position)
                image.image.save(filename, File(fh), save=True)
            image_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. john={john.email} / shop={shop.name} / "
                f"product_id={product.id} / images={image_count}"
            )
        )
