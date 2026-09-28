from django.db import migrations, models
from django.utils import timezone


def retire_link_tokens(apps, schema_editor):
    """Outstanding link tokens can't be redeemed as OTPs; mark them used."""
    now = timezone.now()
    for model_name in ("EmailVerificationToken", "PasswordResetToken"):
        model = apps.get_model("accounts", model_name)
        model.objects.filter(used_at__isnull=True).update(used_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_passwordresettoken"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailverificationtoken",
            name="token",
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="emailverificationtoken",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="passwordresettoken",
            name="token",
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="passwordresettoken",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(retire_link_tokens, migrations.RunPython.noop),
    ]
