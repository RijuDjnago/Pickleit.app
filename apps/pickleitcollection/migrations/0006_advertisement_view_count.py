# Generated by Django 5.1 on 2025-02-26 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pickleitcollection', '0005_advertisement_admin_approve_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='advertisement',
            name='view_count',
            field=models.IntegerField(default=0),
        ),
    ]
