# Generated by Django 5.1 on 2025-01-20 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_rename_full_location_user_current_location_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='latitude',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='longitude',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
