from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('django_ledger', '0030_alter_accountmodel_code_alter_accountmodel_name'),
        ('django_ledger_extensions', '0004_documentinboxitem_externalpaymentrecord'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountingReminderRule',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('vat_quarterly_filing', 'USt-Voranmeldung (quarterly)'), ('monthly_bookkeeping', 'Monthly bookkeeping close'), ('kleinunternehmer_quarterly', 'Kleinunternehmer turnover check'), ('year_end_handoff', 'Year-end Steuerberater handoff'), ('custom', 'Custom deadline')], max_length=32)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('lead_days', models.PositiveIntegerField(default=14, help_text='Send the reminder this many days before the due date.')),
                ('email_to', models.EmailField(blank=True, default='', help_text='Leave blank to use the entity admin email.', max_length=254)),
                ('is_active', models.BooleanField(default=True)),
                ('custom_month', models.PositiveSmallIntegerField(blank=True, help_text='For CUSTOM kind: recurring due date month (1–12).', null=True)),
                ('custom_day', models.PositiveSmallIntegerField(blank=True, help_text='For CUSTOM kind: recurring due date day (1–31).', null=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounting_reminder_rules', to='django_ledger.entitymodel')),
            ],
            options={
                'verbose_name': 'Accounting Reminder Rule',
            },
        ),
        migrations.CreateModel(
            name='AccountingReminderLog',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('period_key', models.CharField(max_length=32)),
                ('due_date', models.DateField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_logs', to='django_ledger_extensions.accountingreminderrule')),
            ],
            options={
                'verbose_name': 'Accounting Reminder Log',
            },
        ),
        migrations.AddField(
            model_name='externalpaymentrecord',
            name='original_payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refund_records', to='django_ledger_extensions.externalpaymentrecord'),
        ),
        migrations.AddField(
            model_name='externalpaymentrecord',
            name='record_type',
            field=models.CharField(choices=[('payment', 'Payment'), ('refund', 'Refund')], default='payment', max_length=16),
        ),
        migrations.AddField(
            model_name='externalpaymentrecord',
            name='staged_transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='external_payment_records', to='django_ledger.stagedtransactionmodel'),
        ),
        migrations.AlterField(
            model_name='externalpaymentrecord',
            name='status',
            field=models.CharField(choices=[('received', 'Received'), ('invoice_draft', 'Draft invoice created'), ('refund_applied', 'Refund applied'), ('manual_action_required', 'Manual action required'), ('failed', 'Failed')], default='received', max_length=32),
        ),
        migrations.AddIndex(
            model_name='externalpaymentrecord',
            index=models.Index(fields=['record_type'], name='django_ledg_record__f3a1c2_idx'),
        ),
        migrations.AddIndex(
            model_name='accountingreminderrule',
            index=models.Index(fields=['entity', 'is_active'], name='django_ledg_entity__b7e4a1_idx'),
        ),
        migrations.AddConstraint(
            model_name='accountingreminderlog',
            constraint=models.UniqueConstraint(fields=('rule', 'period_key'), name='uniq_reminder_sent_per_period'),
        ),
    ]
