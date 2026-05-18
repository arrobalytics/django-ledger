from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_ledger', '0030_enterprise_accounting_foundation'),
    ]

    operations = [
        migrations.AddField(
            model_name='approvalpolicymodel',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='django_ledger.customermodel'),
        ),
        migrations.AddField(
            model_name='approvalpolicymodel',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='django_ledger.vendormodel'),
        ),
    ]