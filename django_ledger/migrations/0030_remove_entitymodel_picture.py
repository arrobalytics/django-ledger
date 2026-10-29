from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("django_ledger", "0029_stagedtransactionmodel_matched_transaction_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="entitymodel",
            name="picture",
        ),
    ]
