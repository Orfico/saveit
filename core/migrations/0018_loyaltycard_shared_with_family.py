from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_transaction_source_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='loyaltycard',
            name='shared_with_family',
            field=models.BooleanField(default=False),
        ),
    ]
