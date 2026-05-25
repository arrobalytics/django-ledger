from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_ledger_extensions', '0002_alter_accounttranslationmodel_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entitytaxprofile',
            name='default_vat_rate',
            field=models.DecimalField(
                decimal_places=4,
                default=0,
                help_text='VAT rate as a decimal fraction (e.g. 0.19). Used only for the standard VAT regime.',
                max_digits=5,
            ),
        ),
        migrations.AlterField(
            model_name='entitytaxprofile',
            name='tax_regime',
            field=models.CharField(
                choices=[
                    ('standard', 'Standard VAT (Regelbesteuerung)'),
                    ('small_business', 'Kleinunternehmer (§ 19 UStG)'),
                    ('exempt', 'Tax-exempt school / training (§ 4 UStG)'),
                ],
                default='exempt',
                help_text='Controls VAT posting behaviour. Change here when your Finanzamt confirms Kleinunternehmer or school exemption status.',
                max_length=32,
            ),
        ),
    ]
