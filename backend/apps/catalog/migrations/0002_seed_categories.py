from django.db import migrations

# Starter global category list (spec.md Assumptions: Administrator-owned, no CRUD UI in this
# feature — research.md §3). Category management is a future Administrator capability.
CATEGORIES = [
    ("Electronics", "electronics"),
    ("Fashion", "fashion"),
    ("Home & Kitchen", "home-kitchen"),
    ("Books", "books"),
    ("Beauty", "beauty"),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for name, slug in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name})


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(slug__in=[slug for _, slug in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
