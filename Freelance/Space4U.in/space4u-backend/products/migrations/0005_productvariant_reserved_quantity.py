from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_productreview"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="reserved_quantity",
            field=models.PositiveIntegerField(default=0),
        ),
    ]


