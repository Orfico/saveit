from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_transaction_paid_by_alter_transaction_is_recurring_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='recurrence_interval',
            field=models.CharField(
                choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('annually', 'Annually'), ('custom', 'Custom')],
                default='monthly',
                help_text='How often this transaction repeats (only relevant when is_recurring=True).',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='transaction',
            name='recurrence_days',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Days between occurrences (only for custom recurrence interval).',
            ),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='is_recurring',
            field=models.BooleanField(
                default=False,
                help_text='If active, this transaction will repeat at the configured interval.',
                verbose_name='Recurring',
            ),
        ),
    ]
