from django.db import migrations, models
import django.db.models.deletion
import django_ledger_extensions.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('django_ledger', '0030_alter_accountmodel_code_alter_accountmodel_name'),
        ('django_ledger_extensions', '0003_alter_entitytaxprofile_tax_regime'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentInboxItem',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(max_length=512, upload_to=django_ledger_extensions.models.document_inbox_upload_to)),
                ('source', models.CharField(choices=[('upload', 'Upload'), ('email', 'Email'), ('camera', 'Camera'), ('api', 'API'), ('webhook', 'Webhook')], default='upload', max_length=32)),
                ('status', models.CharField(choices=[('unlinked', 'Unlinked'), ('linked', 'Linked'), ('archived', 'Archived')], default='unlinked', max_length=32)),
                ('document_type', models.CharField(choices=[('receipt', 'Receipt'), ('invoice', 'Invoice'), ('bank_statement', 'Bank statement'), ('contract', 'Contract'), ('other', 'Other')], default='other', max_length=32)),
                ('description', models.CharField(blank=True, default='', max_length=512)),
                ('vendor_name', models.CharField(blank=True, default='', max_length=255)),
                ('reference', models.CharField(blank=True, default='', max_length=255)),
                ('suggested_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('suggested_date', models.DateField(blank=True, null=True)),
                ('external_source', models.CharField(blank=True, default='', help_text='Third-party connector id, e.g. class_webapp, stripe, email-inbound.', max_length=64)),
                ('external_id', models.CharField(blank=True, default='', max_length=255)),
                ('checksum', models.CharField(blank=True, default='', max_length=64)),
                ('linked_object_id', models.UUIDField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_inbox_items', to='django_ledger.entitymodel')),
                ('linked_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='linked_inbox_items_ct', to='contenttypes.contenttype')),
            ],
            options={
                'verbose_name': 'Document Inbox Item',
            },
        ),
        migrations.CreateModel(
            name='ExternalPaymentRecord',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider', models.CharField(help_text='Connector name, e.g. class_webapp, stripe, paypal.', max_length=64)),
                ('external_id', models.CharField(max_length=255)),
                ('idempotency_key', models.CharField(blank=True, default='', max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=20)),
                ('currency', models.CharField(default='EUR', max_length=3)),
                ('paid_at', models.DateTimeField()),
                ('customer_email', models.EmailField(blank=True, default='', max_length=254)),
                ('customer_name', models.CharField(blank=True, default='', max_length=255)),
                ('product_name', models.CharField(blank=True, default='', max_length=255)),
                ('description', models.CharField(blank=True, default='', max_length=512)),
                ('status', models.CharField(choices=[('received', 'Received'), ('invoice_draft', 'Draft invoice created'), ('failed', 'Failed')], default='received', max_length=32)),
                ('error_message', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='external_payments', to='django_ledger.entitymodel')),
                ('inbox_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='external_payments', to='django_ledger_extensions.documentinboxitem')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='external_payment_records', to='django_ledger.invoicemodel')),
            ],
            options={
                'verbose_name': 'External Payment Record',
            },
        ),
        migrations.AddIndex(
            model_name='documentinboxitem',
            index=models.Index(fields=['entity', 'status'], name='django_ledg_entity__a0d1f8_idx'),
        ),
        migrations.AddIndex(
            model_name='documentinboxitem',
            index=models.Index(fields=['external_source', 'external_id'], name='django_ledg_externa_6a2b0b_idx'),
        ),
        migrations.AddIndex(
            model_name='documentinboxitem',
            index=models.Index(fields=['linked_content_type', 'linked_object_id'], name='django_ledg_linked__fb8d66_idx'),
        ),
        migrations.AddConstraint(
            model_name='documentinboxitem',
            constraint=models.UniqueConstraint(condition=models.Q(('external_id__gt', '')), fields=('entity', 'external_source', 'external_id'), name='uniq_inbox_external_id_per_entity'),
        ),
        migrations.AddIndex(
            model_name='externalpaymentrecord',
            index=models.Index(fields=['entity', 'provider'], name='django_ledg_entity__f8e2d1_idx'),
        ),
        migrations.AddIndex(
            model_name='externalpaymentrecord',
            index=models.Index(fields=['status'], name='django_ledg_status_4c8b2a_idx'),
        ),
        migrations.AddConstraint(
            model_name='externalpaymentrecord',
            constraint=models.UniqueConstraint(fields=('entity', 'provider', 'external_id'), name='uniq_external_payment_per_entity'),
        ),
    ]
