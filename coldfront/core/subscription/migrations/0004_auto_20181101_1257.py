# Generated by Django 2.1.2 on 2018-11-01 16:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('subscription', '0003_auto_20181101_1255'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicalsubscription',
            old_name='end_until',
            new_name='end_date',
        ),
        migrations.RenameField(
            model_name='subscription',
            old_name='end_until',
            new_name='end_date',
        ),
    ]
