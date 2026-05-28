# Generated manually to increase VARCHAR limits for SAP fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0005_update_status_workflow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sapdetail',
            name='plant_code',
            field=models.CharField(help_text='SAP WERKS', max_length=50),
        ),
        migrations.AlterField(
            model_name='sapdetail',
            name='unit_raw',
            field=models.CharField(help_text='Original MEINS', max_length=20),
        ),
        migrations.AlterField(
            model_name='sapdetail',
            name='unit_normalized',
            field=models.CharField(help_text='L, M3, KG, KWH, etc.', max_length=20),
        ),
        migrations.AlterField(
            model_name='sapdetail',
            name='movement_type',
            field=models.CharField(help_text="SAP BWART, e.g., '101'", max_length=20),
        ),
    ]
