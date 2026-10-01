from django.db import migrations, models


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="VENDOR").update(role="CUSTOMER", is_vendor=True)


def backwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_vendor=True).update(role="VENDOR")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_otp_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_vendor",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forwards, backwards),
    ]
