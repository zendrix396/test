from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0008_alter_order_status"),
    ]

    operations = [
        migrations.CreateModel(
            name='RefundConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True)),
                ('cancelled_before_shipment_percent', models.DecimalField(decimal_places=2, default=decimal.Decimal('100.00'), max_digits=5)),
                ('returned_after_shipment_percent', models.DecimalField(decimal_places=2, default=decimal.Decimal('100.00'), max_digits=5)),
            ],
        ),
        migrations.CreateModel(
            name='OrderRefund',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('transaction_id', models.CharField(blank=True, max_length=255)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='refunds', to='commerce.order')),
            ],
        ),
    ]
